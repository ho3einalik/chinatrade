"""
Unit tests for RFQ lifecycle operations and CRM Deal pipeline management.
"""

from decimal import Decimal
import pytest

from trade_hub.db import TradeHubDatabase
from trade_hub.models import RFQStatus, RFQType, DealStage, GlobalIncoterms
from trade_hub.operations.rfq_manager import RFQManager
from trade_hub.operations.deal_manager import DealManager


@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_rfq_deal.db")
    return TradeHubDatabase(db_path=db_file)


def test_rfq_lifecycle_and_conversion_to_deal(temp_db):
    rfq_mgr = RFQManager(temp_db)
    deal_mgr = DealManager(temp_db)

    # 1. Create RFQ
    rfq = rfq_mgr.create_rfq(
        title="Inquiry for 1000 Tons Cement Grade 2",
        product_name="Portland Cement Type 2",
        hs_code="2523.29",
        origin_country="Iran",
        target_country="Iraq",
        target_quantity=Decimal("1000"),
        target_price_usd=Decimal("65.00"),
        incoterms=GlobalIncoterms.FOB
    )
    assert rfq.id is not None
    assert rfq.status == RFQStatus.NEW

    # 2. Transition RFQ status
    ok = rfq_mgr.update_status(rfq.id, RFQStatus.QUALIFIED, notes="Buyer verified via Iraq Chamber")
    assert ok is True

    fetched = temp_db.get_rfq_by_id(rfq.id)
    assert fetched.status == RFQStatus.QUALIFIED
    assert "Iraq Chamber" in fetched.notes

    # 3. Convert RFQ to CRM Deal
    deal = rfq_mgr.convert_to_deal(
        rfq_id=rfq.id,
        buyer_name="Baghdad Builders Union",
        supplier_name="Ilam Cement Factory",
        contract_value_usd=Decimal("65000.00"),
        estimated_cost_usd=Decimal("52000.00"),
        assigned_to="Regional Director"
    )
    assert deal is not None
    assert deal.id is not None
    assert deal.rfq_id == rfq.id
    assert deal.estimated_profit_usd == Decimal("13000.00")
    assert deal.profit_margin_pct == Decimal("20.00")

    # 4. Check that RFQ was updated to NEGOTIATION
    updated_rfq = temp_db.get_rfq_by_id(rfq.id)
    assert updated_rfq.status == RFQStatus.NEGOTIATION


def test_deal_pipeline_progression_and_analytics(temp_db):
    deal_mgr = DealManager(temp_db)

    deal1 = deal_mgr.create_deal(
        deal_title="Export 500 Tons Bitumen to India",
        buyer_name="Mumbai Roads Pvt Ltd",
        supplier_name="Pars Oil Co",
        product_name="Bitumen 60/70",
        quantity=Decimal("500"),
        contract_value_usd=Decimal("200000.00"),
        estimated_cost_usd=Decimal("165000.00"),
        origin_country="Iran",
        destination_country="India",
        stage=DealStage.DISCOVERY
    )
    assert deal1.id is not None

    deal2 = deal_mgr.create_deal(
        deal_title="Export 200 Tons Ceramic Tiles to Iraq",
        buyer_name="Erbil Trading Group",
        supplier_name="Yazd Tile Corp",
        product_name="Ceramic Tiles",
        quantity=Decimal("200"),
        contract_value_usd=Decimal("80000.00"),
        estimated_cost_usd=Decimal("60000.00"),
        origin_country="Iran",
        destination_country="Iraq",
        stage=DealStage.CONTRACT_SIGNED
    )

    # Transition deal1 to NEGOTIATION
    deal_mgr.update_stage(
        deal_id=deal1.id,
        new_stage=DealStage.NEGOTIATION,
        next_action="Review LC draft from Bank of India"
    )

    analytics = deal_mgr.get_pipeline_analytics()
    assert analytics["total_deals"] == 2
    assert analytics["total_pipeline_value_usd"] == 280000.0
    # Weighted value accounts for stage probability
    assert analytics["weighted_pipeline_value_usd"] > 0
    assert analytics["total_estimated_profit_usd"] == 55000.0
