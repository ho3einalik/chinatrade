import pytest
from connectors.base import CircuitBreaker, CircuitBreakerOpenException, ConnectorStatus
from connectors.china_b2b import ChinaB2BConnector
from connectors.manual_entry import ManualQuotationParser
from connectors.digikala import DigikalaConnector

def test_circuit_breaker_mechanism():
    cb = CircuitBreaker(failure_threshold=3, recovery_time_sec=10)
    assert cb.can_execute() is True
    assert cb.is_open is False

    cb.record_failure()
    cb.record_failure()
    assert cb.is_open is False
    assert cb.can_execute() is True

    # 3rd failure trips the circuit breaker
    cb.record_failure()
    assert cb.is_open is True
    assert cb.can_execute() is False

    # Success resets breaker
    cb.record_success()
    assert cb.is_open is False
    assert cb.can_execute() is True

def test_china_b2b_connector_platforms():
    conn = ChinaB2BConnector()
    links = conn.generate_search_links("智能手表 T1000")

    assert "ehsy" in links
    assert "gongchang" in links
    assert "makepolo" in links
    assert "qipeiren" in links
    assert "1688" in links
    assert "chemnet" in links

    # Verify verified live statuses
    assert links["ehsy"]["status"] == ConnectorStatus.LIVE_VERIFIED
    assert links["gongchang"]["status"] == ConnectorStatus.LIVE_VERIFIED
    assert links["makepolo"]["status"] == ConnectorStatus.LIVE_VERIFIED
    assert links["qipeiren"]["status"] == ConnectorStatus.GEO_BLOCKED_OR_CHALLENGED
    assert links["nala"]["status"] == ConnectorStatus.DECOMMISSIONED_OR_DOWN

    # Verify query encoding
    assert "ehsy.com/search?keyword=" in links["ehsy"]["url"]
    assert "gongchang.com/search?q=" in links["gongchang"]["url"]

def test_manual_quotation_parser_from_dict():
    data = {
        "name": "Guangzhou Audio Pro Co.",
        "platform": "WeChat PI #2026-04",
        "product_title": "TWS ANC Earbuds Pro 4",
        "unit_price_cny": 58.5,
        "moq": 500,
        "weight_kg": 0.08,
        "volume_cbm": 0.0004,
        "price_tiers": [
            {"min_quantity": 500, "unit_price_cny": 58.5},
            {"min_quantity": 2000, "unit_price_cny": 52.0}
        ]
    }

    supp = ManualQuotationParser.parse_dict_to_supplier(data)
    assert supp.name == "Guangzhou Audio Pro Co."
    assert supp.unit_price_cny == 58.5
    assert supp.moq == 500
    assert len(supp.price_tiers) == 2
    assert supp.price_tiers[1].unit_price_cny == 52.0

def test_manual_quotation_parser_from_csv():
    csv_text = """name,platform,product_title,unit_price_cny,moq,weight_kg,volume_cbm,lead_time_days
Shenzhen MaxPower,1688 Factory,Power Bank 20000mAh 65W,62.0,200,0.42,0.0006,12
Dongguan Cable Tech,Direct Factory,Braided Type-C Cable 100W,3.8,1000,0.03,0.0001,5
"""
    suppliers = ManualQuotationParser.parse_csv_content(csv_text)
    assert len(suppliers) == 2
    assert suppliers[0].product_title == "Power Bank 20000mAh 65W"
    assert suppliers[0].unit_price_cny == 62.0
    assert suppliers[0].moq == 200
    assert suppliers[1].unit_price_cny == 3.8
    assert suppliers[1].moq == 1000
