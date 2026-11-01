"""
CRM Deal Operations & Pipeline Manager for Trade Intelligence Hub.
Tracks international B2B deals from discovery to contract, shipment, and closing.
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone

from trade_hub.models import DealRecord, DealStage, GlobalIncoterms
from trade_hub.db import TradeHubDatabase, DEFAULT_TRADE_DB_PATH


class DealManager:
    """
    Manages international sales contracts, import/export shipments, and pipeline progression.
    """

    # Probability weighting for each stage to calculate expected pipeline revenue
    STAGE_WEIGHTS: Dict[DealStage, Decimal] = {
        DealStage.DISCOVERY: Decimal("0.10"),
        DealStage.LEAD_QUALIFIED: Decimal("0.20"),
        DealStage.RFQ_ISSUED: Decimal("0.35"),
        DealStage.QUOTATION_RECEIVED: Decimal("0.50"),
        DealStage.NEGOTIATION: Decimal("0.65"),
        DealStage.CONTRACT_SIGNED: Decimal("0.85"),
        DealStage.PAYMENT_PENDING: Decimal("0.90"),
        DealStage.IN_PRODUCTION: Decimal("0.95"),
        DealStage.SHIPPED: Decimal("0.98"),
        DealStage.CUSTOMS_CLEARED: Decimal("0.99"),
        DealStage.CLOSED_WON: Decimal("1.00"),
        DealStage.CLOSED_LOST: Decimal("0.00"),
    }

    def __init__(self, db: Optional[TradeHubDatabase] = None):
        self.db = db or TradeHubDatabase()

    def create_deal(
        self,
        deal_title: str,
        buyer_name: str,
        supplier_name: str,
        product_name: str,
        quantity: Decimal,
        contract_value_usd: Decimal,
        estimated_cost_usd: Decimal,
        origin_country: str,
        destination_country: str,
        stage: DealStage = DealStage.DISCOVERY,
        hs_code: Optional[str] = None,
        unit: str = "Tons",
        incoterms: GlobalIncoterms = GlobalIncoterms.FOB,
        assigned_to: str = "Trade Manager",
        next_action: str = "Draft Proforma Invoice",
        next_followup_date: Optional[str] = None,
        rfq_id: Optional[int] = None,
        tenant_id: str = "default_importer"
    ) -> DealRecord:
        """
        Creates and stores a new international trade deal.
        """
        val = Decimal(str(contract_value_usd))
        cost = Decimal(str(estimated_cost_usd))
        profit = val - cost
        margin_pct = ((profit / val) * Decimal("100")).quantize(Decimal("0.01")) if val > Decimal("0") else Decimal("0")

        deal = DealRecord(
            tenant_id=tenant_id,
            deal_title=deal_title.strip(),
            stage=stage,
            rfq_id=rfq_id,
            buyer_name=buyer_name.strip(),
            supplier_name=supplier_name.strip(),
            product_name=product_name.strip(),
            hs_code=hs_code.strip() if hs_code else None,
            quantity=quantity,
            unit=unit.strip(),
            contract_value_usd=val,
            estimated_cost_usd=cost,
            estimated_profit_usd=profit,
            profit_margin_pct=margin_pct,
            origin_country=origin_country.strip(),
            destination_country=destination_country.strip(),
            incoterms=incoterms,
            assigned_to=assigned_to.strip(),
            next_action=next_action.strip(),
            next_followup_date=next_followup_date
        )

        deal_id = self.db.save_deal(deal)
        deal.id = deal_id
        self.db.log_audit("CREATE_DEAL", "DEAL", deal_id, f"Created deal '{deal.deal_title}' (${val:,.2f})", tenant_id)
        return deal

    def update_stage(
        self,
        deal_id: int,
        new_stage: DealStage,
        next_action: Optional[str] = None,
        next_followup_date: Optional[str] = None,
        win_loss_reason: Optional[str] = None,
        tenant_id: str = "default_importer"
    ) -> bool:
        """
        Transitions a deal across pipeline stages.
        """
        existing = self.db.get_deal_by_id(deal_id, tenant_id=tenant_id)
        if not existing:
            return False

        action = next_action or existing.next_action
        followup = next_followup_date or existing.next_followup_date
        reason = win_loss_reason or existing.win_loss_reason

        ok = self.db.update_deal_stage(
            deal_id=deal_id,
            new_stage=new_stage,
            next_action=action,
            next_followup_date=followup,
            win_loss_reason=reason,
            tenant_id=tenant_id
        )
        if ok:
            self.db.log_audit("UPDATE_DEAL_STAGE", "DEAL", deal_id, f"Transitioned to stage {new_stage.value}", tenant_id)
        return ok

    def list_deals(
        self,
        tenant_id: str = "default_importer",
        stage: Optional[DealStage] = None,
        assigned_to: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 50
    ) -> List[DealRecord]:
        """
        Retrieves deals with filtering.
        """
        deals = self.db.list_deals(tenant_id=tenant_id, stage=stage, limit=limit)
        if assigned_to:
            deals = [d for d in deals if d.assigned_to.lower() == assigned_to.lower()]
        if search_query:
            q = search_query.lower().strip()
            deals = [
                d for d in deals
                if q in d.deal_title.lower()
                or q in d.buyer_name.lower()
                or q in d.supplier_name.lower()
                or q in d.product_name.lower()
            ]
        return deals

    def get_pipeline_analytics(self, tenant_id: str = "default_importer") -> Dict[str, Any]:
        """
        Computes weighted pipeline metrics, stage distribution, and profit forecasts.
        """
        all_deals = self.db.list_deals(tenant_id=tenant_id, limit=1000)
        total_deals = len(all_deals)

        total_value = Decimal("0")
        weighted_value = Decimal("0")
        total_profit = Decimal("0")

        stage_counts: Dict[str, int] = {s.value: 0 for s in DealStage}
        closed_won_value = Decimal("0")
        closed_won_count = 0

        for d in all_deals:
            stage_counts[d.stage.value] = stage_counts.get(d.stage.value, 0) + 1
            if d.stage != DealStage.CLOSED_LOST:
                total_value += d.contract_value_usd
                weight = self.STAGE_WEIGHTS.get(d.stage, Decimal("0.10"))
                weighted_value += (d.contract_value_usd * weight)
                total_profit += d.estimated_profit_usd

            if d.stage == DealStage.CLOSED_WON:
                closed_won_value += d.contract_value_usd
                closed_won_count += 1

        avg_margin = (
            ((total_profit / total_value) * Decimal("100")).quantize(Decimal("0.1"))
            if total_value > Decimal("0") else Decimal("0.0")
        )

        return {
            "total_deals": total_deals,
            "total_pipeline_value_usd": float(total_value),
            "weighted_pipeline_value_usd": float(weighted_value.quantize(Decimal("0.01"))),
            "total_estimated_profit_usd": float(total_profit),
            "average_profit_margin_pct": float(avg_margin),
            "closed_won_count": closed_won_count,
            "closed_won_value_usd": float(closed_won_value),
            "stage_distribution": stage_counts
        }
