import pytest
from core.ranking import OpportunityRankingEngine
from core.verification import SupplierVerificationEngine
from core.regulations import ImportRegulationsEngine
from core.matching import MatchClassification
from core.models import ChineseSupplier

def test_opportunity_score_decoupling_from_confidence():
    # Scenario: High theoretical profit (85% ROI) but very shaky data (weak match, no live data, 0 samples)
    eval_low_conf = OpportunityRankingEngine.evaluate(
        net_margin_pct=35.0,
        roi_pct=85.0,
        sales_velocity_score=8,
        active_sellers_count=5,
        supplier_years=1,
        supplier_has_certs=False,
        has_radio_or_health_barrier=False,
        is_live_iran_data=False,
        match_classification=MatchClassification.WEAK,
        iran_sample_count=0
    )

    # Opportunity is commercially attractive, but data confidence MUST be penalized
    assert eval_low_conf.profitability_score >= 9.0
    assert eval_low_conf.data_confidence_score < 50.0  # Decoupled!

    # Scenario 2: Solid data (Live API, Exact match, 10 samples)
    eval_high_conf = OpportunityRankingEngine.evaluate(
        net_margin_pct=35.0,
        roi_pct=85.0,
        sales_velocity_score=8,
        active_sellers_count=5,
        supplier_years=6,
        supplier_has_certs=True,
        has_radio_or_health_barrier=False,
        is_live_iran_data=True,
        match_classification=MatchClassification.EXACT,
        iran_sample_count=10
    )

    assert eval_high_conf.data_confidence_score >= 85.0
    assert "طلایی" in eval_high_conf.recommendation_verdict

def test_supplier_verification_flags_and_audit():
    # 1. Suspicious new trading company
    shady_supplier = ChineseSupplier(
        name="Shenzhen Fast Wealth Global Trading Co., Ltd.",
        platform="1688",
        product_title="Smart Watch T1000",
        unit_price_cny=0.5, # Unrealistic low price
        years_active=0,
        certifications=[],
        moq=10
    )

    audit = SupplierVerificationEngine.audit_supplier(shady_supplier, category="الکترونیک")
    assert audit.is_factory is False
    assert audit.risk_level in ("HIGH", "CRITICAL")
    assert any("سابقه کمتر از ۱ سال" in f for f in audit.red_flags)
    assert any("قیمت غیرعادی" in f for f in audit.red_flags)

    # 2. Legitimate certified manufacturer
    good_supplier = ChineseSupplier(
        name="Dongguan Precision Electronics Manufacturing Co., Ltd.",
        platform="1688 Factory",
        product_title="Smart Watch T1000 Ultra",
        unit_price_cny=42.0,
        years_active=7,
        certifications=["CE", "RoHS", "ISO9001"],
        location="Guangdong, Shenzhen",
        moq=500
    )

    audit_good = SupplierVerificationEngine.audit_supplier(good_supplier, category="الکترونیک")
    assert audit_good.is_factory is True
    assert audit_good.risk_level in ("LOW", "MEDIUM")
    assert audit_good.safety_score >= 7.5
    assert not audit_good.red_flags

def test_regulations_and_hs_code_analysis():
    # Electronic wireless device requires CRA radio certification
    res_watch = ImportRegulationsEngine.analyze_compliance("ساعت هوشمند T1000 Ultra سیم کارت خور", category="الکترونیک")
    assert res_watch.is_radio_equipment is True
    assert res_watch.primary_hs_code == "8517.62.90"
    assert any("CRA" in lic or "تنظیم مقررات" in lic for lic in res_watch.mandatory_licenses)

    # Polymer raw material
    res_pvc = ImportRegulationsEngine.analyze_compliance("پودر PVC گرید S-65", category="پتروشیمی")
    assert res_pvc.is_radio_equipment is False
    assert res_pvc.primary_hs_code == "3904.10.00"
    assert any("استاندارد" in lic for lic in res_pvc.mandatory_licenses)
