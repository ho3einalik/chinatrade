"""
Domain Models and Data Schemas for Trade Intelligence Hub.
Provides strictly typed, Decimal-precise, and validated data contracts.
Isolated from China Import domain schemas.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------

class TradeRole(str, Enum):
    BUYER = "BUYER"
    SUPPLIER = "SUPPLIER"
    BOTH = "BOTH"
    AGENT = "AGENT"


class EvidenceType(str, Enum):
    OFFICIAL_CUSTOMS = "OFFICIAL_CUSTOMS"          # UN Comtrade, National Customs
    VERIFIED_CONTRACT = "VERIFIED_CONTRACT"        # PI, BL, signed contract
    DIRECT_COMPANY_QUOTE = "DIRECT_COMPANY_QUOTE"  # Verified manufacturer quote
    OFFICIAL_CHAMBER = "OFFICIAL_CHAMBER"          # Joint Chamber, TPO
    PUBLIC_DIRECTORY = "PUBLIC_DIRECTORY"          # ParsGoods, trade directories
    ECONOMETRIC_ESTIMATE = "ECONOMETRIC_ESTIMATE"  # ITC Export Potential, statistical model
    USER_MANUAL = "USER_MANUAL"                    # Entered directly by user in CRM
    DEMO_FIXTURE = "DEMO_FIXTURE"                  # Testing sandbox only


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"              # Direct official government / verified contract
    MEDIUM = "MEDIUM"          # Reputable trade chamber / direct quote
    LOW = "LOW"                # Public web directory / econometric model
    UNVERIFIED = "UNVERIFIED"  # Preliminary unvetted lead


class VerificationStatus(str, Enum):
    OFFICIAL_VERIFIED = "OFFICIAL_VERIFIED"  # Verified by official registry / documents
    PRELIMINARY_MATCH = "PRELIMINARY_MATCH"  # Domain and corporate identity verified
    NEEDS_REVIEW = "NEEDS_REVIEW"            # Missing corporate tax / registry records
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"  # Only contact info, no verifiable documents
    RED_FLAG = "RED_FLAG"                    # Known fraudulent pattern, domain spoof


class GlobalIncoterms(str, Enum):
    EXW = "EXW"  # Ex Works (درب کارخانه)
    FCA = "FCA"  # Free Carrier (تحویل به حمل‌کننده)
    FAS = "FAS"  # Free Alongside Ship (کنار کشتی)
    FOB = "FOB"  # Free on Board (روی عرشه)
    CFR = "CFR"  # Cost and Freight (هزینه و کرایه)
    CIF = "CIF"  # Cost, Insurance and Freight (بهای کالا، بیمه و کرایه)
    CPT = "CPT"  # Carriage Paid To (کرایه حمل پرداخت‌شده)
    CIP = "CIP"  # Carriage and Insurance Paid To (کرایه و بیمه پرداخت‌شده)
    DAP = "DAP"  # Delivered at Place (تحویل در محل)
    DPU = "DPU"  # Delivered at Place Unloaded (تحویل در محل تخلیه)
    DDP = "DDP"  # Delivered Duty Paid (تحویل با پرداخت حقوق و عوارض)


class RFQType(str, Enum):
    RFQ = "RFQ"                      # استعلام قیمت رسمی
    RFP = "RFP"                      # درخواست طرح و پروپوزال
    TENDER = "TENDER"                # مناقصه بین‌المللی
    BUYER_LEAD = "BUYER_LEAD"        # فرصت خریدار شناسایی‌شده
    SUPPLIER_LEAD = "SUPPLIER_LEAD"  # فرصت تأمین‌کننده شناسایی‌شده
    SALES_OFFER = "SALES_OFFER"      # پیشنهاد فروش صادراتی
    PURCHASE_OFFER = "PURCHASE_OFFER"# پیشنهاد خرید


class RFQStatus(str, Enum):
    NEW = "NEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    QUALIFIED = "QUALIFIED"
    CONTACTED = "CONTACTED"
    NEGOTIATION = "NEGOTIATION"
    QUOTATION = "QUOTATION"
    WON = "WON"
    LOST = "LOST"
    EXPIRED = "EXPIRED"


class DealStage(str, Enum):
    DISCOVERY = "DISCOVERY"
    LEAD_QUALIFIED = "LEAD_QUALIFIED"
    RFQ_ISSUED = "RFQ_ISSUED"
    QUOTATION_RECEIVED = "QUOTATION_RECEIVED"
    NEGOTIATION = "NEGOTIATION"
    CONTRACT_SIGNED = "CONTRACT_SIGNED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    IN_PRODUCTION = "IN_PRODUCTION"
    SHIPPED = "SHIPPED"
    CUSTOMS_CLEARED = "CUSTOMS_CLEARED"
    CLOSED_WON = "CLOSED_WON"
    CLOSED_LOST = "CLOSED_LOST"


class TradeDirection(str, Enum):
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    TRANSIT = "TRANSIT"
    CROSS_BORDER = "CROSS_BORDER"


# --------------------------------------------------------------------------
# Normalized Trade Record
# --------------------------------------------------------------------------

class NormalizedTradeRecord(BaseModel):
    """
    Standard schema for all global trade statistics & market evidence.
    """
    source_id: str = Field(..., description="Unique source adapter identifier")
    source_name: str = Field(..., description="Official title of the source (e.g. ITC Trade Map)")
    source_url: str = Field("", description="Direct link or reference URL")
    external_record_id: Optional[str] = None
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    published_at: Optional[str] = None
    data_period: str = Field("2024", description="Statistical period (e.g. 2024-Annual, 2025-Q2)")
    
    country_origin: str = Field(..., description="ISO 2/3 code or country name")
    country_destination: str = Field(..., description="Target market ISO or country name")
    hs_code: str = Field(..., description="Harmonized System Code (2 to 8 digits)")
    
    product_title_en: str = Field("", description="English product description")
    product_title_fa: str = Field("", description="Persian product title")
    
    trade_value_usd: Decimal = Field(default=Decimal("0"), description="Total dollar trade value")
    trade_quantity: Optional[Decimal] = Field(default=None, description="Physical trade quantity")
    quantity_unit: str = Field("Tons", description="Unit of measurement (Tons, KG, Pieces)")
    unit_value_usd: Optional[Decimal] = Field(default=None, description="Calculated USD price per unit")
    
    annual_growth_rate_pct: Optional[Decimal] = None
    market_share_pct: Optional[Decimal] = None
    
    evidence_type: EvidenceType = Field(default=EvidenceType.OFFICIAL_CUSTOMS)
    confidence_level: ConfidenceLevel = Field(default=ConfidenceLevel.HIGH)
    is_mirror_data: bool = Field(default=False, description="Whether data is reported by trade partner")
    notes: str = Field("", description="Caveats, data limitations, or methodology remarks")


# --------------------------------------------------------------------------
# HS Code Candidates
# --------------------------------------------------------------------------

class HSCodeCandidate(BaseModel):
    hs_code: str
    description_en: str
    description_fa: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    rationale: str
    tariff_estimate_pct: Optional[Decimal] = None


# --------------------------------------------------------------------------
# My Trade Network (Private Contacts & Entities)
# --------------------------------------------------------------------------

class PrivateContact(BaseModel):
    """
    Confidential business partner (Buyer, Supplier, or Both) in My Trade Network.
    Strictly isolated from external queries and other users.
    """
    id: Optional[int] = None
    tenant_id: str = Field(default="default_importer", description="Data isolation tenant key")
    name: str = Field(..., description="Company name or individual contact title")
    country: str = Field(..., description="Country of establishment")
    city: str = Field("", description="City/Province")
    role: TradeRole = Field(default=TradeRole.BOTH, description="BUYER, SUPPLIER, or BOTH")
    
    contact_person: str = Field("", description="Primary key executive name")
    email: str = Field("", description="Official email address")
    phone: str = Field("", description="Phone/WhatsApp/WeChat")
    website: str = Field("", description="Official web domain")
    address: str = Field("", description="Physical office or factory address")
    
    products: List[str] = Field(default_factory=list, description="List of tradeable products")
    hs_codes: List[str] = Field(default_factory=list, description="Target HS codes")
    
    capacity_monthly: str = Field("", description="Supply capacity or monthly purchasing demand")
    moq: Optional[int] = Field(default=None, description="Minimum Order Quantity")
    
    unit_price_usd: Optional[Decimal] = Field(default=None, description="Quoted unit price in USD")
    price_validity_date: Optional[str] = None
    payment_terms: str = Field("T/T, L/C, Cash Against Documents", description="Accepted payment terms")
    incoterms: GlobalIncoterms = Field(default=GlobalIncoterms.FOB)
    lead_time_days: Optional[int] = Field(default=None, description="Production or delivery lead time")
    
    certifications: List[str] = Field(default_factory=list, description="ISO, CE, Halal, etc.")
    source_reference: str = Field("Manual Entry", description="How user met this contact")
    verification_status: VerificationStatus = Field(default=VerificationStatus.PRELIMINARY_MATCH)
    
    private_notes: str = Field("", description="Confidential negotiation or credit history")
    tags: List[str] = Field(default_factory=list, description="Custom user tags")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# --------------------------------------------------------------------------
# RFQ & Lead Operations
# --------------------------------------------------------------------------

class RFQRecord(BaseModel):
    id: Optional[int] = None
    tenant_id: str = "default_importer"
    rfq_type: RFQType = Field(default=RFQType.RFQ)
    status: RFQStatus = Field(default=RFQStatus.NEW)
    title: str = Field(..., description="Descriptive title of request")
    product_name: str
    hs_code: Optional[str] = None
    
    origin_country: str = "Iran"
    target_country: str = "Iraq"
    target_quantity: Decimal = Field(default=Decimal("1000"))
    unit: str = "Tons"
    target_price_usd: Optional[Decimal] = None
    
    incoterms: GlobalIncoterms = GlobalIncoterms.CIF
    payment_terms: str = "L/C at sight / T/T"
    deadline_date: Optional[str] = None
    
    contact_id: Optional[int] = Field(default=None, description="Linked PrivateContact ID")
    contact_name: Optional[str] = None
    evidence_source: str = Field("Private RFQ", description="Source link or verification basis")
    
    specs_summary: str = Field("", description="Key technical and grade specifications")
    notes: str = Field("")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# --------------------------------------------------------------------------
# CRM Deal Management
# --------------------------------------------------------------------------

class DealRecord(BaseModel):
    id: Optional[int] = None
    tenant_id: str = "default_importer"
    deal_title: str
    stage: DealStage = Field(default=DealStage.DISCOVERY)
    
    rfq_id: Optional[int] = None
    buyer_name: str
    supplier_name: str
    product_name: str
    hs_code: Optional[str] = None
    
    quantity: Decimal
    unit: str = "Tons"
    contract_value_usd: Decimal
    estimated_cost_usd: Decimal
    estimated_profit_usd: Decimal
    profit_margin_pct: Decimal
    
    origin_country: str
    destination_country: str
    incoterms: GlobalIncoterms = GlobalIncoterms.FOB
    
    assigned_to: str = "Trade Manager"
    next_action: str = "Send Proforma Invoice"
    next_followup_date: Optional[str] = None
    win_loss_reason: Optional[str] = None
    
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# --------------------------------------------------------------------------
# Multi-Vector Matching Model
# --------------------------------------------------------------------------

class MatchingBreakdown(BaseModel):
    technical_fit_score: float = Field(..., ge=0, le=100)
    commercial_fit_score: float = Field(..., ge=0, le=100)
    logistics_fit_score: float = Field(..., ge=0, le=100)
    regulatory_fit_score: float = Field(..., ge=0, le=100)
    evidence_confidence_score: float = Field(..., ge=0, le=100)
    data_freshness_score: float = Field(..., ge=0, le=100)


class EntityMatchResult(BaseModel):
    entity_name: str
    entity_country: str
    entity_role: TradeRole
    is_private_network: bool
    overall_match_score: float = Field(..., ge=0, le=100)
    classification: str = Field("EXACT", description="EXACT, CLOSE_WITH_DIFFERENCES, WEAK, INSUFFICIENT_DATA")
    breakdown: MatchingBreakdown
    matched_specs: List[str] = Field(default_factory=list)
    discrepancies: List[str] = Field(default_factory=list)
    unknown_parameters: List[str] = Field(default_factory=list)
    recommended_action: str = ""
    buyer_type: Optional[str] = None
    purchasing_capacity: Optional[str] = None
    city_province: Optional[str] = None
    payment_terms_expected: Optional[str] = None
    contact_channel: Optional[str] = None


# --------------------------------------------------------------------------
# Global Trade Cost Calculator Models
# --------------------------------------------------------------------------

class GlobalTradeCostLineItem(BaseModel):
    category: str  # origin, freight, customs, clearance, financing, risk
    name_fa: str
    name_en: str
    amount_usd: Decimal
    amount_irr: Decimal
    percentage_of_total: Decimal


class GlobalTradeCalculationResult(BaseModel):
    origin_country: str
    destination_country: str
    incoterms: GlobalIncoterms
    trade_direction: TradeDirection
    batch_quantity: Decimal
    unit_name: str
    
    currency_used: str = "USD"
    fx_rate_usd_irr: Decimal
    
    purchase_cost_per_unit_usd: Decimal
    total_landed_cost_per_unit_usd: Decimal
    total_landed_cost_batch_usd: Decimal
    
    target_selling_price_per_unit_usd: Decimal
    gross_revenue_batch_usd: Decimal
    
    net_profit_per_unit_usd: Decimal
    total_net_profit_batch_usd: Decimal
    profit_margin_pct: Decimal
    markup_roi_pct: Decimal
    
    break_even_selling_price_usd: Decimal
    break_even_units: Decimal
    
    line_items: List[GlobalTradeCostLineItem] = Field(default_factory=list)
    sensitivity_fx_10pct_usd: Decimal = Decimal("0")
    sensitivity_freight_20pct_usd: Decimal = Decimal("0")
    is_sufficient_data: bool = True
    assumptions_notes: str = ""


# --------------------------------------------------------------------------
# Journey Dossiers
# --------------------------------------------------------------------------

class MarketEntryDossier(BaseModel):
    """Output of Journey 1: 'I have a product to sell'"""
    product_name_fa: str
    product_name_en: str
    hs_code_primary: str
    hs_code_candidates: List[HSCodeCandidate] = Field(default_factory=list)
    top_importing_countries: List[NormalizedTradeRecord] = Field(default_factory=list)
    competitor_exporting_countries: List[NormalizedTradeRecord] = Field(default_factory=list)
    market_size_usd: Decimal = Decimal("0")
    annual_market_growth_pct: Decimal = Decimal("0")
    tariff_barriers_summary: str = ""
    candidate_buyers: List[EntityMatchResult] = Field(default_factory=list)
    export_cost_estimate: Optional[GlobalTradeCalculationResult] = None
    draft_sales_pitch_en: str = ""
    draft_sales_pitch_fa: str = ""
    action_roadmap: List[str] = Field(default_factory=list)
    data_confidence_score: float = 0.0
    sources_cited: List[str] = Field(default_factory=list)
    domestic_buyers: List[EntityMatchResult] = Field(default_factory=list)
    domestic_market_summary: Optional[Dict[str, Any]] = None


class SourcingDossier(BaseModel):
    """Output of Journey 2: 'I need a product to buy'"""
    product_name: str
    origin_country_preference: Optional[str] = None
    destination_country: str = "Iran"
    required_specs: Dict[str, Any] = Field(default_factory=dict)
    candidate_suppliers: List[EntityMatchResult] = Field(default_factory=list)
    private_network_hits_count: int = 0
    external_sources_hits_count: int = 0
    estimated_landed_cost: Optional[GlobalTradeCalculationResult] = None
    recommended_procurement_strategy: str = ""
    verification_alerts: List[str] = Field(default_factory=list)
    data_confidence_score: float = 0.0
    sources_cited: List[str] = Field(default_factory=list)


class OpportunityDiscoveryDossier(BaseModel):
    """Output of Journey 3: 'I don't know what to trade' (Demand Radar)"""
    sector_or_tag: str
    discovered_opportunities: List[Dict[str, Any]] = Field(default_factory=list)
    active_buyer_leads: List[RFQRecord] = Field(default_factory=list)
    high_growth_products: List[Dict[str, Any]] = Field(default_factory=list)
    untapped_export_potential_markets: List[Dict[str, Any]] = Field(default_factory=list)
    filter_criteria_applied: Dict[str, Any] = Field(default_factory=dict)
    data_period_analyzed: str = "2023-2025"
    sources_cited: List[str] = Field(default_factory=list)
