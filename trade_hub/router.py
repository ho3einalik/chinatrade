"""
FastAPI Router for Trade Intelligence Hub.
Mounts all independent endpoints under /api/trade-hub.
Strictly isolated from China Import APIs.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from typing import List, Optional, Dict, Any
from decimal import Decimal
import io

from trade_hub.models import (
    TradeRole,
    GlobalIncoterms,
    TradeDirection,
    RFQType,
    RFQStatus,
    DealStage,
    PrivateContact,
    RFQRecord,
    DealRecord,
    MarketEntryDossier,
    SourcingDossier,
    OpportunityDiscoveryDossier,
    GlobalTradeCalculationResult
)
from trade_hub.db import TradeHubDatabase
from trade_hub.sources.registry import TradeSourcesRegistry
from trade_hub.sources.trademap import TradeMapAdapter
from trade_hub.network.repository import TradeNetworkRepository
from trade_hub.network.importer import NetworkBatchImporter
from trade_hub.operations.cost_calculator import GlobalTradeCostCalculator
from trade_hub.operations.rfq_manager import RFQManager
from trade_hub.operations.deal_manager import DealManager
from trade_hub.intelligence.journey_seller import SellerJourneyEngine
from trade_hub.intelligence.journey_buyer import BuyerJourneyEngine
from trade_hub.intelligence.journey_discovery import DiscoveryJourneyEngine
from trade_hub.intelligence.company_verification import CompanyVerificationEngine

trade_hub_router = APIRouter()

# Singletons / Service instances
db = TradeHubDatabase()
registry = TradeSourcesRegistry()
network_repo = TradeNetworkRepository(db)
rfq_manager = RFQManager(db)
deal_manager = DealManager(db)
seller_engine = SellerJourneyEngine(db, registry, network_repo)
buyer_engine = BuyerJourneyEngine(db, registry, network_repo)
discovery_engine = DiscoveryJourneyEngine(db, registry)


# --------------------------------------------------------------------------
# 1. External Trade Sources & Trade Map
# --------------------------------------------------------------------------

@trade_hub_router.get("/sources", summary="List external trade intelligence sources")
def get_trade_sources():
    """Returns metadata and operational status for all registered trade databases."""
    return registry.list_sources()


@trade_hub_router.get("/sources/search-links", summary="Generate direct research URLs")
def get_source_links(
    hs_code: Optional[str] = Query(None, description="HS 6-digit code"),
    country: Optional[str] = Query(None, description="Target country name or ISO"),
    product_name: Optional[str] = Query(None, description="Product keywords")
):
    """Generates direct, authentic deep-links for Trade Map, Comtrade, MacMap, and Chambers."""
    links = {}
    tm_adapter = registry.get_adapter("trademap")
    if hs_code:
        links["itc_trade_map"] = tm_adapter.build_search_url(query=product_name or "", hs_code=hs_code, country=country) if tm_adapter else f"https://www.trademap.org"
        links["un_comtrade"] = f"https://comtradeplus.un.org/TradeFlow?frequency=A&flowCode=M&reporterCode=&cmdCode={hs_code.replace('.', '')}"
        links["macmap"] = f"https://www.macmap.org/en//results?product={hs_code.replace('.', '')}&country_partner={country or ''}"
    if country and "iraq" in country.lower():
        links["iran_iraq_chamber"] = "https://iriqcc.ir/"
    links["tpo_iran"] = "https://tpo.ir/trade-agreements"
    links["parsgoods"] = f"https://parsgoods.com/search?q={product_name or ''}"
    return {"links": links}


@trade_hub_router.post("/upload-trademap-csv", summary="Upload and parse ITC Trade Map CSV export")
async def upload_trademap_csv(file: UploadFile = File(...)):
    """
    Parses a user-downloaded CSV/TSV export from ITC Trade Map.
    Stores records in trade_hub.db and returns normalized statistics.
    """
    try:
        content = await file.read()
        text_content = content.decode("utf-8-sig", errors="replace")
        records = TradeMapAdapter.parse_csv_export(text_content)
        saved_count = 0
        for r in records:
            db.save_trade_record(r)
            saved_count += 1
        return {
            "status": "success",
            "parsed_records": len(records),
            "saved_records": saved_count,
            "filename": file.filename,
            "sample_records": [r.model_dump(mode="json") for r in records[:5]]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse Trade Map CSV: {str(e)}")


# --------------------------------------------------------------------------
# 2. My Trade Network (Private Contacts & CRM)
# --------------------------------------------------------------------------

@trade_hub_router.get("/network/contacts", response_model=List[PrivateContact], summary="List private network contacts")
def list_private_contacts(
    query: Optional[str] = None,
    role: Optional[TradeRole] = None,
    country: Optional[str] = None,
    tenant_id: str = "default_importer"
):
    """Retrieves private counterparties with priority product search."""
    return network_repo.search_contacts(
        product_query=query,
        role=role,
        country=country,
        tenant_id=tenant_id
    )


@trade_hub_router.post("/network/contacts", response_model=PrivateContact, summary="Add contact to My Trade Network")
def add_private_contact(contact: PrivateContact, tenant_id: str = "default_importer"):
    """Creates a new private contact with de-duplication checks."""
    try:
        contact.tenant_id = tenant_id
        saved = network_repo.save_contact(contact)
        return saved
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@trade_hub_router.post("/network/upload-csv", summary="Batch import contacts from CSV")
async def upload_network_csv(file: UploadFile = File(...), tenant_id: str = "default_importer"):
    """
    Imports private contacts from CSV with CSV formula injection sanitization.
    """
    try:
        content = await file.read()
        text_content = content.decode("utf-8-sig", errors="replace")
        result = NetworkBatchImporter.import_csv(text_content, tenant_id=tenant_id, db=db)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSV import failed: {str(e)}")


@trade_hub_router.get("/network/stats", summary="Get My Trade Network statistics")
def get_network_statistics(tenant_id: str = "default_importer"):
    """Returns total contacts, buyer/supplier breakdown, and top countries."""
    return network_repo.get_network_stats(tenant_id=tenant_id)


# --------------------------------------------------------------------------
# 3. The 3 Intelligence Journeys
# --------------------------------------------------------------------------

class SellerJourneyRequest(Dict[str, Any]):
    pass

@trade_hub_router.post("/journey/seller", response_model=MarketEntryDossier, summary="Journey 1: I have a product to sell")
def execute_seller_journey(payload: Dict[str, Any], tenant_id: str = "default_importer"):
    """
    Analyzes global demand, target import countries, candidate buyers, and export margins.
    """
    product_name = payload.get("product_name")
    if not product_name:
        raise HTTPException(status_code=400, detail="product_name is required")

    origin = payload.get("origin_country", "Iran")
    target = payload.get("target_country")
    unit_cost = Decimal(str(payload["unit_cost_usd"])) if payload.get("unit_cost_usd") is not None else None
    qty = Decimal(str(payload.get("batch_quantity", 100)))
    unit_name = payload.get("unit_name", "Tons")

    return seller_engine.execute(
        product_name=product_name,
        origin_country=origin,
        target_country=target,
        unit_cost_usd=unit_cost,
        batch_quantity=qty,
        unit_name=unit_name,
        tenant_id=tenant_id
    )


@trade_hub_router.post("/journey/buyer", response_model=SourcingDossier, summary="Journey 2: I need a product to buy")
def execute_buyer_journey(payload: Dict[str, Any], tenant_id: str = "default_importer"):
    """
    Searches private suppliers first, runs multi-vector matching, and computes landed cost.
    """
    product_name = payload.get("product_name")
    if not product_name:
        raise HTTPException(status_code=400, detail="product_name is required")

    origin_pref = payload.get("origin_country_preference")
    dest = payload.get("destination_country", "Iran")
    specs = payload.get("required_specs", {})
    qty = Decimal(str(payload.get("batch_quantity", 50)))
    unit_name = payload.get("unit_name", "Tons")
    target_price = Decimal(str(payload["target_price_usd"])) if payload.get("target_price_usd") is not None else None

    return buyer_engine.execute(
        product_name=product_name,
        origin_country_preference=origin_pref,
        destination_country=dest,
        required_specs=specs,
        batch_quantity=qty,
        unit_name=unit_name,
        target_price_usd=target_price,
        tenant_id=tenant_id
    )


@trade_hub_router.get("/journey/discovery", response_model=OpportunityDiscoveryDossier, summary="Journey 3: Opportunity Discovery (Demand Radar)")
def execute_discovery_journey(
    sector: str = Query("all", description="Sector: all, petrochemicals, building_materials, agrifood, metals"),
    min_growth_pct: float = Query(4.0, description="Minimum annual import growth %"),
    tenant_id: str = "default_importer"
):
    """
    Scans trade databases to detect emerging export niches, trade corridors, and buyer leads.
    """
    return discovery_engine.execute(
        sector=sector,
        min_growth_pct=min_growth_pct,
        tenant_id=tenant_id
    )


# --------------------------------------------------------------------------
# 4. RFQ & Deal Operations
# --------------------------------------------------------------------------

@trade_hub_router.get("/rfqs", response_model=List[RFQRecord], summary="List RFQs and Leads")
def list_rfqs(
    status: Optional[RFQStatus] = None,
    rfq_type: Optional[RFQType] = None,
    query: Optional[str] = None,
    tenant_id: str = "default_importer"
):
    """Lists RFQs with optional filtering."""
    return rfq_manager.list_rfqs(
        tenant_id=tenant_id,
        status=status,
        rfq_type=rfq_type,
        search_query=query
    )


@trade_hub_router.post("/rfqs", response_model=RFQRecord, summary="Create new RFQ or Trade Lead")
def create_rfq(payload: Dict[str, Any], tenant_id: str = "default_importer"):
    """Creates a new RFQ entry."""
    title = payload.get("title") or f"استعلام خرید {payload.get('product_name')}"
    product_name = payload.get("product_name")
    if not product_name:
        raise HTTPException(status_code=400, detail="product_name is required")

    return rfq_manager.create_rfq(
        title=title,
        product_name=product_name,
        rfq_type=RFQType(payload.get("rfq_type", RFQType.RFQ.value)),
        hs_code=payload.get("hs_code"),
        origin_country=payload.get("origin_country", "Iran"),
        target_country=payload.get("target_country", "Iraq"),
        target_quantity=Decimal(str(payload.get("target_quantity", 1000))),
        unit=payload.get("unit", "Tons"),
        target_price_usd=Decimal(str(payload["target_price_usd"])) if payload.get("target_price_usd") is not None else None,
        incoterms=GlobalIncoterms(payload.get("incoterms", GlobalIncoterms.CIF.value)),
        payment_terms=payload.get("payment_terms", "L/C at sight / T/T"),
        deadline_date=payload.get("deadline_date"),
        contact_id=payload.get("contact_id"),
        contact_name=payload.get("contact_name"),
        evidence_source=payload.get("evidence_source", "Private Inquiry"),
        specs_summary=payload.get("specs_summary", ""),
        notes=payload.get("notes", ""),
        tenant_id=tenant_id
    )


@trade_hub_router.post("/rfqs/{rfq_id}/status", summary="Update RFQ Status")
def update_rfq_status(rfq_id: int, payload: Dict[str, Any], tenant_id: str = "default_importer"):
    """Transitions RFQ status."""
    new_status = RFQStatus(payload.get("status"))
    notes = payload.get("notes")
    ok = rfq_manager.update_status(rfq_id, new_status, notes=notes, tenant_id=tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="RFQ not found")
    return {"status": "success", "new_status": new_status.value}


@trade_hub_router.post("/rfqs/{rfq_id}/convert-to-deal", response_model=DealRecord, summary="Convert RFQ to Deal")
def convert_rfq_to_deal(rfq_id: int, payload: Dict[str, Any], tenant_id: str = "default_importer"):
    """Converts a qualified RFQ to an active CRM deal."""
    buyer = payload.get("buyer_name", "خریدار تجاری")
    supplier = payload.get("supplier_name", "تأمین‌کننده طرف قرارداد")
    val = Decimal(str(payload.get("contract_value_usd", 100000)))
    cost = Decimal(str(payload.get("estimated_cost_usd", 85000)))

    deal = rfq_manager.convert_to_deal(
        rfq_id=rfq_id,
        buyer_name=buyer,
        supplier_name=supplier,
        contract_value_usd=val,
        estimated_cost_usd=cost,
        tenant_id=tenant_id
    )
    if not deal:
        raise HTTPException(status_code=404, detail="RFQ not found")
    return deal


@trade_hub_router.get("/deals", response_model=List[DealRecord], summary="List Deals in CRM Pipeline")
def list_deals(
    stage: Optional[DealStage] = None,
    assigned_to: Optional[str] = None,
    query: Optional[str] = None,
    tenant_id: str = "default_importer"
):
    """Lists deals across CRM pipeline stages."""
    return deal_manager.list_deals(
        tenant_id=tenant_id,
        stage=stage,
        assigned_to=assigned_to,
        search_query=query
    )


@trade_hub_router.post("/deals", response_model=DealRecord, summary="Create Deal")
def create_deal(payload: Dict[str, Any], tenant_id: str = "default_importer"):
    """Creates a new deal directly."""
    return deal_manager.create_deal(
        deal_title=payload.get("deal_title", "معامله جدید"),
        buyer_name=payload.get("buyer_name", "خریدار"),
        supplier_name=payload.get("supplier_name", "تأمین‌کننده"),
        product_name=payload.get("product_name", "کالا"),
        quantity=Decimal(str(payload.get("quantity", 100))),
        contract_value_usd=Decimal(str(payload.get("contract_value_usd", 50000))),
        estimated_cost_usd=Decimal(str(payload.get("estimated_cost_usd", 40000))),
        origin_country=payload.get("origin_country", "Iran"),
        destination_country=payload.get("destination_country", "Iraq"),
        stage=DealStage(payload.get("stage", DealStage.DISCOVERY.value)),
        hs_code=payload.get("hs_code"),
        unit=payload.get("unit", "Tons"),
        incoterms=GlobalIncoterms(payload.get("incoterms", GlobalIncoterms.FOB.value)),
        assigned_to=payload.get("assigned_to", "Trade Manager"),
        next_action=payload.get("next_action", "Send Proforma Invoice"),
        tenant_id=tenant_id
    )


@trade_hub_router.post("/deals/{deal_id}/stage", summary="Update Deal Stage")
def update_deal_stage(deal_id: int, payload: Dict[str, Any], tenant_id: str = "default_importer"):
    """Updates deal stage and next action in CRM pipeline."""
    new_stage = DealStage(payload.get("stage"))
    next_action = payload.get("next_action")
    followup = payload.get("next_followup_date")
    reason = payload.get("win_loss_reason")

    ok = deal_manager.update_stage(
        deal_id=deal_id,
        new_stage=new_stage,
        next_action=next_action,
        next_followup_date=followup,
        win_loss_reason=reason,
        tenant_id=tenant_id
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Deal not found")
    return {"status": "success", "stage": new_stage.value}


@trade_hub_router.get("/deals/analytics", summary="CRM Pipeline Analytics")
def get_deal_analytics(tenant_id: str = "default_importer"):
    """Calculates weighted pipeline revenue, stage counts, and profit forecasts."""
    return deal_manager.get_pipeline_analytics(tenant_id=tenant_id)


# --------------------------------------------------------------------------
# 5. Global Cost Calculator & Company Verification
# --------------------------------------------------------------------------

@trade_hub_router.post("/calculate-cost", response_model=GlobalTradeCalculationResult, summary="Calculate Landed Cost and Margins")
def calculate_trade_cost(payload: Dict[str, Any]):
    """
    Arbitrary-route, multi-Incoterm landed cost and margin calculator.
    """
    origin = payload.get("origin_country", "Iran")
    dest = payload.get("destination_country", "Iraq")
    incoterm = GlobalIncoterms(payload.get("incoterms", GlobalIncoterms.FOB.value))
    direction = TradeDirection(payload.get("trade_direction", TradeDirection.EXPORT.value))
    qty = Decimal(str(payload.get("batch_quantity", 100)))
    unit_cost = Decimal(str(payload.get("purchase_cost_per_unit_usd", 500)))
    target_sell = Decimal(str(payload["target_selling_price_per_unit_usd"])) if payload.get("target_selling_price_per_unit_usd") is not None else None
    unit_name = payload.get("unit_name", "Tons")
    tariff_pct = Decimal(str(payload.get("customs_tariff_pct", "0.05")))
    vat_pct = Decimal(str(payload.get("vat_tax_pct", "0.09")))
    freight = Decimal(str(payload["freight_per_unit_usd"])) if payload.get("freight_per_unit_usd") is not None else None

    return GlobalTradeCostCalculator.calculate(
        origin_country=origin,
        destination_country=dest,
        incoterms=incoterm,
        trade_direction=direction,
        batch_quantity=qty,
        purchase_cost_per_unit_usd=unit_cost,
        target_selling_price_per_unit_usd=target_sell,
        unit_name=unit_name,
        customs_tariff_pct=tariff_pct,
        vat_tax_pct=vat_pct,
        freight_per_unit_usd=freight
    )


@trade_hub_router.post("/verify-company", summary="Verify company & counterparty risk")
def verify_company(payload: Dict[str, Any]):
    """Performs multi-point risk and verification audit on a counterparty."""
    contact = PrivateContact(
        name=payload.get("name", "شرکت آزمایشی"),
        country=payload.get("country", "UAE"),
        city=payload.get("city", ""),
        email=payload.get("email", ""),
        website=payload.get("website", ""),
        address=payload.get("address", ""),
        payment_terms=payload.get("payment_terms", "T/T"),
        certifications=payload.get("certifications", []),
        private_notes=payload.get("private_notes", "")
    )
    return CompanyVerificationEngine.evaluate_contact(contact)


@trade_hub_router.get("/audit-logs", summary="List Trade Hub audit logs")
def get_audit_logs(limit: int = 50):
    """Retrieves recent audit logs for Trade Hub operations."""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM th_audit_logs ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cursor.fetchall()]
