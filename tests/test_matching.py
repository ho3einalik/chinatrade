import pytest
from core.matching import ProductMatchingEngine, MatchClassification, StandardUnits

def test_unit_normalization():
    # Weight
    assert StandardUnits.normalize_weight_kg(500, "g") == 0.5
    assert StandardUnits.normalize_weight_kg(2, "ton") == 2000.0
    assert abs(StandardUnits.normalize_weight_kg(1, "lb") - 0.453592) < 0.001

    # Dimensions & CBM
    assert StandardUnits.normalize_dimension_cm(150, "mm") == 15.0
    assert StandardUnits.normalize_dimension_cm(2, "m") == 200.0
    cbm = StandardUnits.calculate_cbm(50, 40, 50) # 50x40x50 cm = 100,000 cm3 = 0.1 CBM
    assert abs(cbm - 0.1) < 0.0001

    # Battery
    assert StandardUnits.normalize_battery_mah(5, "Ah") == 5000.0
    # Power
    assert StandardUnits.normalize_power_watt(1.5, "kW") == 1500.0

def test_exact_or_close_match():
    engine = ProductMatchingEngine()
    iran_title = "ساعت هوشمند مدل T1000 Ultra صفحه نمایش AMOLED ضد آب"
    china_title = "Smart Watch T1000 Ultra AMOLED IP68 Waterproof OEM Factory"

    match = engine.compare_products(
        iran_title=iran_title,
        iran_specs_dict={},
        china_title=china_title,
        china_specs_dict={},
        category="گجت‌ها و الکترونیک مصرفی"
    )

    assert match.classification in (MatchClassification.EXACT, MatchClassification.CLOSE_WITH_DIFFERENCES)
    assert match.score >= 70.0
    assert any("T1000" in p or "کد مدل" in p for p in match.pros)
    assert not match.cons

def test_mismatched_model_classification():
    engine = ProductMatchingEngine()
    iran_title = "پودر PVC گرید S-65 اروند پتروشیمی"
    china_title = "PVC Resin Suspension S-70 High Molecular Weight"

    match = engine.compare_products(
        iran_title=iran_title,
        iran_specs_dict={},
        china_title=china_title,
        china_specs_dict={},
        category="مواد اولیه و پتروشیمی"
    )

    # Should detect discrepancy between S-65 and S-70
    assert any("مغایرت" in c for c in match.cons)
    assert match.classification in (MatchClassification.CLOSE_WITH_DIFFERENCES, MatchClassification.WEAK)

def test_industrial_tool_matching():
    engine = ProductMatchingEngine()
    iran_title = "دریل شارژی براشلس 21 ولت چکشی دو سرعته"
    china_title = "Brushless Cordless Drill 21V Impact Driver Dual Speed"

    match = engine.compare_products(
        iran_title=iran_title,
        iran_specs_dict={},
        china_title=china_title,
        china_specs_dict={},
        category="ابزارآلات صنعتی و شارژی"
    )

    assert match.classification in (MatchClassification.EXACT, MatchClassification.CLOSE_WITH_DIFFERENCES)
    assert match.score >= 75.0
    assert any("21" in p for p in match.pros)
    assert any("brushless" in p for p in match.pros)

def test_insufficient_data_match():
    engine = ProductMatchingEngine()
    iran_title = "کالای با کیفیت عالی و درجه یک صادراتی"
    china_title = "High Quality Hot Selling Factory Direct Item"

    match = engine.compare_products(
        iran_title=iran_title,
        iran_specs_dict={},
        china_title=china_title,
        china_specs_dict={},
        category="general"
    )

    assert match.classification in (MatchClassification.INSUFFICIENT_DATA, MatchClassification.WEAK)
    assert match.is_conditional is True
