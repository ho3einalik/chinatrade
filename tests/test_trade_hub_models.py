"""
Unit tests for Trade Intelligence Hub domain models and schemas.
"""

from decimal import Decimal
import pytest
from trade_hub.models import (
    TradeRole,
    EvidenceType,
    ConfidenceLevel,
    VerificationStatus,
    GlobalIncoterms,
    RFQType,
    RFQStatus,
    DealStage,
    TradeDirection,
    NormalizedTradeRecord,
    HSCodeCandidate,
    PrivateContact,
    RFQRecord,
    DealRecord,
    GlobalTradeCostLineItem,
    GlobalTradeCalculationResult,
    MarketEntryDossier,
    SourcingDossier,
    OpportunityDiscoveryDossier
)


def test_normalized_trade_record_decimal_precision():
    rec = NormalizedTradeRecord(
        source_id="un_comtrade",
        source_name="UN Comtrade",
        source_url="https://comtradeplus.un.org",
        country_origin="Iran",
        country_destination="Iraq",
        hs_code="2713.20",
        trade_value_usd=Decimal("125000000.50"),
        trade_quantity=Decimal("250000.00"),
        quantity_unit="Tons",
        unit_value_usd=Decimal("500.00"),
        annual_growth_rate_pct=Decimal("7.25"),
        evidence_type=EvidenceType.OFFICIAL_CUSTOMS,
        confidence_level=ConfidenceLevel.HIGH
    )
    assert rec.trade_value_usd == Decimal("125000000.50")
    assert rec.unit_value_usd == Decimal("500.00")
    assert rec.evidence_type == EvidenceType.OFFICIAL_CUSTOMS
    assert rec.confidence_level == ConfidenceLevel.HIGH


def test_private_contact_model():
    contact = PrivateContact(
        name="Basra Bitumen Corp",
        country="Iraq",
        city="Basra",
        role=TradeRole.BUYER,
        email="procurement@basrabitumen.iq",
        products=["Bitumen 60/70", "Polymer modified asphalt"],
        hs_codes=["2713.20"],
        unit_price_usd=Decimal("410.00"),
        incoterms=GlobalIncoterms.CIF,
        verification_status=VerificationStatus.PRELIMINARY_MATCH
    )
    assert contact.name == "Basra Bitumen Corp"
    assert contact.role == TradeRole.BUYER
    assert contact.incoterms == GlobalIncoterms.CIF
    assert len(contact.products) == 2


def test_rfq_and_deal_models():
    rfq = RFQRecord(
        title="Official Inquiry for 500 Tons Bitumen",
        product_name="Bitumen 60/70",
        hs_code="2713.20",
        origin_country="Iran",
        target_country="Iraq",
        target_quantity=Decimal("500"),
        target_price_usd=Decimal("420.00"),
        incoterms=GlobalIncoterms.FOB
    )
    assert rfq.rfq_type == RFQType.RFQ
    assert rfq.status == RFQStatus.NEW

    deal = DealRecord(
        deal_title="Deal: Bitumen 60/70 - Basra Bitumen Corp",
        stage=DealStage.RFQ_ISSUED,
        buyer_name="Basra Bitumen Corp",
        supplier_name="Iran Bitumen Exporter",
        product_name="Bitumen 60/70",
        quantity=Decimal("500"),
        contract_value_usd=Decimal("210000.00"),
        estimated_cost_usd=Decimal("180000.00"),
        estimated_profit_usd=Decimal("30000.00"),
        profit_margin_pct=Decimal("14.29"),
        origin_country="Iran",
        destination_country="Iraq"
    )
    assert deal.contract_value_usd == Decimal("210000.00")
    assert deal.estimated_profit_usd == Decimal("30000.00")
    assert deal.profit_margin_pct == Decimal("14.29")


def test_global_calculation_result_model():
    item = GlobalTradeCostLineItem(
        category="freight",
        name_fa="کرایه حمل بین‌المللی",
        name_en="International Freight",
        amount_usd=Decimal("22500.00"),
        amount_irr=Decimal("19125000000"),
        percentage_of_total=Decimal("12.50")
    )
    res = GlobalTradeCalculationResult(
        origin_country="Iran",
        destination_country="Iraq",
        incoterms=GlobalIncoterms.FOB,
        trade_direction=TradeDirection.EXPORT,
        batch_quantity=Decimal("500"),
        unit_name="Tons",
        fx_rate_usd_irr=Decimal("850000"),
        purchase_cost_per_unit_usd=Decimal("350.00"),
        total_landed_cost_per_unit_usd=Decimal("385.00"),
        total_landed_cost_batch_usd=Decimal("192500.00"),
        target_selling_price_per_unit_usd=Decimal("450.00"),
        gross_revenue_batch_usd=Decimal("225000.00"),
        net_profit_per_unit_usd=Decimal("65.00"),
        total_net_profit_batch_usd=Decimal("32500.00"),
        profit_margin_pct=Decimal("14.44"),
        markup_roi_pct=Decimal("16.88"),
        break_even_selling_price_usd=Decimal("385.00"),
        break_even_units=Decimal("427.78"),
        line_items=[item]
    )
    assert res.total_net_profit_batch_usd == Decimal("32500.00")
    assert res.break_even_selling_price_usd == Decimal("385.00")
