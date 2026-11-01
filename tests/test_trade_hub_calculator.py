"""
Unit tests for Global Trade Cost & Landed Profit Calculator.
Verifies Decimal precision, Incoterms shifting, line-item auditing, and sensitivity analysis.
"""

from decimal import Decimal
import pytest
from trade_hub.models import GlobalIncoterms, TradeDirection
from trade_hub.operations.cost_calculator import GlobalTradeCostCalculator


def test_export_iran_to_iraq_fob():
    """
    Test export calculation under FOB Incoterms from Iran to Iraq.
    """
    res = GlobalTradeCostCalculator.calculate(
        origin_country="Iran",
        destination_country="Iraq",
        incoterms=GlobalIncoterms.FOB,
        trade_direction=TradeDirection.EXPORT,
        batch_quantity=Decimal("500"),
        purchase_cost_per_unit_usd=Decimal("380.00"),
        target_selling_price_per_unit_usd=Decimal("560.00"),
        unit_name="Tons",
        fx_rate_usd_irr=Decimal("850000"),
        freight_per_unit_usd=Decimal("45.00"),
        customs_tariff_pct=Decimal("0.05")
    )

    assert isinstance(res.total_landed_cost_batch_usd, Decimal)
    assert res.total_landed_cost_per_unit_usd > Decimal("380.00")
    assert res.net_profit_per_unit_usd == res.target_selling_price_per_unit_usd - res.total_landed_cost_per_unit_usd
    assert res.total_net_profit_batch_usd == res.net_profit_per_unit_usd * Decimal("500")
    assert res.profit_margin_pct > Decimal("0")
    assert res.markup_roi_pct > Decimal("0")
    assert res.break_even_selling_price_usd == res.total_landed_cost_per_unit_usd
    assert res.break_even_units > Decimal("0")
    assert len(res.line_items) == 9
    assert res.sensitivity_fx_10pct_usd > Decimal("0")
    assert res.sensitivity_freight_20pct_usd > Decimal("0")


def test_import_turkey_to_iran_cif():
    """
    Test import calculation under CIF Incoterms from Turkey to Iran.
    Under CIF, seller already paid freight and insurance, so applicable freight is zero in buyer landed addition.
    """
    res = GlobalTradeCostCalculator.calculate(
        origin_country="Turkey",
        destination_country="Iran",
        incoterms=GlobalIncoterms.CIF,
        trade_direction=TradeDirection.IMPORT,
        batch_quantity=Decimal("100"),
        purchase_cost_per_unit_usd=Decimal("1200.00"),
        target_selling_price_per_unit_usd=Decimal("1550.00"),
        customs_tariff_pct=Decimal("0.04"),
        vat_tax_pct=Decimal("0.09")
    )

    assert res.total_landed_cost_per_unit_usd > Decimal("1200.00")
    assert res.profit_margin_pct > Decimal("0")
    assert res.currency_used == "USD"


def test_ddp_incoterm_duty_prepaid():
    """
    Under DDP, the seller delivers with all import duties and VAT prepaid in the purchase price.
    """
    res = GlobalTradeCostCalculator.calculate(
        origin_country="UAE",
        destination_country="Iran",
        incoterms=GlobalIncoterms.DDP,
        trade_direction=TradeDirection.IMPORT,
        batch_quantity=Decimal("50"),
        purchase_cost_per_unit_usd=Decimal("2000.00"),
        target_selling_price_per_unit_usd=Decimal("2300.00")
    )
    # Duty and VAT line items should be 0 since seller prepaid them
    duty_item = next(i for i in res.line_items if i.name_en == "Destination Customs Tariff")
    vat_item = next(i for i in res.line_items if i.name_en == "Destination VAT & Taxes")
    assert duty_item.amount_usd == Decimal("0.00")
    assert vat_item.amount_usd == Decimal("0.00")
