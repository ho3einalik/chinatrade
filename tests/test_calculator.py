import pytest
from decimal import Decimal
from core.calculator import ImportProfitCalculator, RULE_VERSION
from core.models import ChineseSupplier, PriceTier
from config import TradeConfig

@pytest.fixture
def test_supplier():
    return ChineseSupplier(
        name="Shenzhen TopTech Electronics Co., Ltd.",
        platform="1688",
        product_title="Smart Watch T1000 Ultra AMOLED",
        unit_price_cny=45.0,
        price_tiers=[
            PriceTier(min_quantity=100, unit_price_cny=45.0),
            PriceTier(min_quantity=500, unit_price_cny=40.0),
            PriceTier(min_quantity=1000, unit_price_cny=36.0),
        ],
        moq=100,
        weight_kg=0.15,
        volume_cbm=0.0008,
        lead_time_days=7
    )

def test_volumetric_weight_calculation():
    # 50cm x 40cm x 30cm / 5000 = 60,000 / 5000 = 12.0 kg
    vol_kg = ImportProfitCalculator.calculate_volumetric_weight(50, 40, 30, divisor=5000)
    assert vol_kg == Decimal("12.000")

def test_chargeable_weight_air_vs_sea(test_supplier):
    calc = ImportProfitCalculator()
    
    # Air cargo: supplier weight 0.15kg, volume 0.0008 cbm -> 0.0008 * 167 = 0.1336 kg
    # max(0.15, 0.1336) = 0.15 kg
    air_weight = calc.calculate_chargeable_weight(test_supplier.weight_kg, test_supplier.volume_cbm, "Air Cargo")
    assert air_weight == Decimal("0.15")

    # If bulky: 0.1kg actual but 0.01 cbm volume -> 0.01 * 167 = 1.67 kg
    bulky_air = calc.calculate_chargeable_weight(0.1, 0.01, "Air Cargo")
    assert bulky_air == Decimal("1.67")

    # Sea freight uses CBM
    sea_cbm = calc.calculate_chargeable_weight(test_supplier.weight_kg, test_supplier.volume_cbm, "Sea Freight")
    assert sea_cbm == Decimal("0.0008")

def test_3_scenarios_ranking_and_metrics(test_supplier):
    calc = ImportProfitCalculator()
    target_iran_price = 1_450_000 # 1.45M Toman
    
    res = calc.calculate_landed_cost_scenarios(
        supplier=test_supplier,
        target_iran_price_toman=target_iran_price,
        shipping_method="Air Cargo",
        batch_quantity=500
    )

    assert res.rule_version == RULE_VERSION
    assert res.batch_quantity == 500
    
    # Quantity tier discount applied: 500 pcs -> 40 CNY (instead of 45)
    r = res.realistic
    opt = res.optimistic
    pess = res.pessimistic

    # Landed costs relationship: Pessimistic > Realistic > Optimistic
    assert pess.landed_cost_unit_toman > r.landed_cost_unit_toman > opt.landed_cost_unit_toman

    # Profit relationship: Optimistic > Realistic > Pessimistic
    assert opt.net_profit_unit_toman > r.net_profit_unit_toman > pess.net_profit_unit_toman

    # Margin and ROI validation
    assert opt.roi_percent > r.roi_percent > pess.roi_percent
    assert opt.margin_percent > r.margin_percent > pess.margin_percent

    # Break-even checks
    assert r.break_even_price_toman > 0
    assert r.break_even_units >= 1
    assert r.break_even_units <= 500

    # Line items completeness
    assert len(r.line_items) == 13
    assert any(item.name_en == "vat" for item in r.line_items)
    assert any(item.name_en == "financing_cost" for item in r.line_items)
    assert any(item.name_en == "remittance_fee" for item in r.line_items)

def test_legacy_breakdown_compatibility(test_supplier):
    calc = ImportProfitCalculator()
    legacy = calc.calculate_landed_cost(
        supplier=test_supplier,
        target_iran_price_toman=1_200_000,
        shipping_method="Sea Freight",
        batch_quantity=200
    )

    assert legacy.total_landed_cost_toman > 0
    assert legacy.batch_quantity == 200
    assert legacy.shipping_method == "Sea Freight"
    assert legacy.break_even_price_toman > 0
    assert legacy.profit_margin_percent is not None
