"""
RFQ & Trade Lead Lifecycle Operations Manager.
Orchestrates RFQ creation, state transitions, validation, and conversion to CRM Deals.
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone

from trade_hub.models import RFQRecord, RFQStatus, RFQType, DealRecord, DealStage, GlobalIncoterms
from trade_hub.db import TradeHubDatabase, DEFAULT_TRADE_DB_PATH


class RFQManager:
    """
    Manages international trade RFQs, buyer/supplier inquiry requests, and conversion pipelines.
    """

    def __init__(self, db: Optional[TradeHubDatabase] = None):
        self.db = db or TradeHubDatabase()

    def create_rfq(
        self,
        title: str,
        product_name: str,
        rfq_type: RFQType = RFQType.RFQ,
        hs_code: Optional[str] = None,
        origin_country: str = "Iran",
        target_country: str = "Iraq",
        target_quantity: Decimal = Decimal("1000"),
        unit: str = "Tons",
        target_price_usd: Optional[Decimal] = None,
        incoterms: GlobalIncoterms = GlobalIncoterms.CIF,
        payment_terms: str = "L/C at sight / T/T",
        deadline_date: Optional[str] = None,
        contact_id: Optional[int] = None,
        contact_name: Optional[str] = None,
        evidence_source: str = "Private Inquiry",
        specs_summary: str = "",
        notes: str = "",
        tenant_id: str = "default_importer"
    ) -> RFQRecord:
        """
        Creates and stores a validated RFQ record.
        """
        rfq = RFQRecord(
            tenant_id=tenant_id,
            rfq_type=rfq_type,
            status=RFQStatus.NEW,
            title=title.strip(),
            product_name=product_name.strip(),
            hs_code=hs_code.strip() if hs_code else None,
            origin_country=origin_country.strip(),
            target_country=target_country.strip(),
            target_quantity=target_quantity,
            unit=unit.strip(),
            target_price_usd=target_price_usd,
            incoterms=incoterms,
            payment_terms=payment_terms.strip(),
            deadline_date=deadline_date,
            contact_id=contact_id,
            contact_name=contact_name.strip() if contact_name else None,
            evidence_source=evidence_source.strip(),
            specs_summary=specs_summary.strip(),
            notes=notes.strip()
        )
        rfq_id = self.db.save_rfq(rfq)
        rfq.id = rfq_id
        self.db.log_audit("CREATE_RFQ", "RFQ", rfq_id, f"Created RFQ '{rfq.title}' for {rfq.product_name}", tenant_id)
        return rfq

    def update_status(self, rfq_id: int, new_status: RFQStatus, notes: Optional[str] = None, tenant_id: str = "default_importer") -> bool:
        """
        Transitions an RFQ through its operational state machine.
        """
        existing = self.db.get_rfq_by_id(rfq_id, tenant_id=tenant_id)
        if not existing:
            return False

        updated_notes = existing.notes
        if notes:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            updated_notes = f"{existing.notes}\n[{ts}] Status changed to {new_status.value}: {notes}".strip()

        ok = self.db.update_rfq_status(rfq_id, new_status, updated_notes, tenant_id=tenant_id)
        if ok:
            self.db.log_audit("UPDATE_RFQ_STATUS", "RFQ", rfq_id, f"Updated status to {new_status.value}", tenant_id)
        return ok

    def list_rfqs(
        self,
        tenant_id: str = "default_importer",
        status: Optional[RFQStatus] = None,
        rfq_type: Optional[RFQType] = None,
        search_query: Optional[str] = None,
        limit: int = 50
    ) -> List[RFQRecord]:
        """
        Lists and filters RFQs for a specific tenant.
        """
        rfqs = self.db.list_rfqs(tenant_id=tenant_id, status=status, limit=limit)
        if rfq_type:
            rfqs = [r for r in rfqs if r.rfq_type == rfq_type]
        if search_query:
            q = search_query.lower().strip()
            rfqs = [
                r for r in rfqs
                if q in r.title.lower()
                or q in r.product_name.lower()
                or (r.hs_code and q in r.hs_code.lower())
                or (r.contact_name and q in r.contact_name.lower())
            ]
        return rfqs

    def convert_to_deal(
        self,
        rfq_id: int,
        buyer_name: str,
        supplier_name: str,
        contract_value_usd: Decimal,
        estimated_cost_usd: Decimal,
        assigned_to: str = "Trade Manager",
        next_action: str = "Draft Proforma Invoice",
        tenant_id: str = "default_importer"
    ) -> Optional[DealRecord]:
        """
        Converts a qualified RFQ directly into a CRM Deal pipeline stage.
        """
        rfq = self.db.get_rfq_by_id(rfq_id, tenant_id=tenant_id)
        if not rfq:
            return None

        val = Decimal(str(contract_value_usd))
        cost = Decimal(str(estimated_cost_usd))
        profit = val - cost
        margin_pct = ((profit / val) * Decimal("100")).quantize(Decimal("0.01")) if val > Decimal("0") else Decimal("0")

        deal = DealRecord(
            tenant_id=tenant_id,
            deal_title=f"معامله: {rfq.product_name} - {buyer_name}",
            stage=DealStage.RFQ_ISSUED,
            rfq_id=rfq.id,
            buyer_name=buyer_name,
            supplier_name=supplier_name,
            product_name=rfq.product_name,
            hs_code=rfq.hs_code,
            quantity=rfq.target_quantity,
            unit=rfq.unit,
            contract_value_usd=val,
            estimated_cost_usd=cost,
            estimated_profit_usd=profit,
            profit_margin_pct=margin_pct,
            origin_country=rfq.origin_country,
            destination_country=rfq.target_country,
            incoterms=rfq.incoterms,
            assigned_to=assigned_to,
            next_action=next_action
        )

        deal_id = self.db.save_deal(deal)
        deal.id = deal_id

        # Update RFQ status to QUALIFIED / NEGOTIATION
        self.update_status(rfq_id, RFQStatus.NEGOTIATION, f"تبدیل به معامله فعال #{deal_id}", tenant_id=tenant_id)
        self.db.log_audit("CONVERT_RFQ_TO_DEAL", "RFQ", rfq_id, f"Converted to Deal #{deal_id}", tenant_id)
        return deal

    def get_stats(self, tenant_id: str = "default_importer") -> Dict[str, Any]:
        """
        Returns RFQ pipeline summary metrics.
        """
        all_rfqs = self.db.list_rfqs(tenant_id=tenant_id, limit=1000)
        total = len(all_rfqs)
        active = sum(1 for r in all_rfqs if r.status not in [RFQStatus.WON, RFQStatus.LOST, RFQStatus.EXPIRED])
        won = sum(1 for r in all_rfqs if r.status == RFQStatus.WON)
        total_val = sum((r.target_price_usd or Decimal("0")) * r.target_quantity for r in all_rfqs)
        
        return {
            "total_rfqs": total,
            "active_rfqs": active,
            "won_rfqs": won,
            "win_rate_pct": round((won / total * 100), 1) if total > 0 else 0.0,
            "total_pipeline_usd": float(total_val)
        }
