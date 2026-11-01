"""
Comprehensive unit & integration tests covering search resilience,
decoupled concepts, scenario simulations, and data provenance.
"""

import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from core.agent import ChinaIranImportAgent
from core.models import DataType, ComponentStatus, VerificationStatus
from core.china_sourcing import ChinaSourcingEngine
from core.iran_market import IranMarketEngine
from core.db import Database
from connectors.base import ConnectorStatus

@pytest.fixture
def agent_instance():
    return ChinaIranImportAgent()

def test_1_both_buy_and_sell_prices_present(agent_instance):
    """
    Scenario 1: Both buy price and sell price are verified and present.
    Expectation: definite_profit_calculable is True, mode is DEFINITE_CONTRACT,
    scenarios are populated with real numbers.
    """
    result = agent_instance.analyze_product_comprehensive(
        product_query="ساعت هوشمند تست",
        custom_target_iran_price=2500000.0,
        custom_buy_price_cny=50.0,
        batch_quantity=200
    )

    assert result["definite_profit_calculable"] is True
    assert result["is_simulation"] is False
    assert result["insufficient_data"] is False
    
    prov = result["data_provenance"]
    assert prov["calculation_mode"] == "DEFINITE_CONTRACT"
    assert prov["supplier_price_status"] == ComponentStatus.USER_MANUAL.value
    assert prov["iran_market_status"] == ComponentStatus.USER_MANUAL.value
    assert prov["supplier_price_value"] == 50.0
    assert prov["iran_market_value_toman"] == 2500000.0
    
    # Scenarios must be fully populated
    assert result["sea_scenarios"]["is_sufficient_data"] is True
    assert result["sea_scenarios"]["realistic"]["net_profit_unit_toman"] > 0
    assert result["air_scenarios"]["is_sufficient_data"] is True

def test_2_only_buy_price_present(agent_instance):
    """
    Scenario 2: Only buy price is present, Iran market price is unavailable.
    Expectation: definite_profit_calculable is False, calculation_mode is DISCOVERY_ONLY,
    missing_requirements notes market price, but regulations/links are complete.
    """
    # Mock iran_market engine to return no results
    with patch.object(agent_instance.market_engine, "analyze_iran_market") as mock_market:
        from core.models import IranMarketPrice, DataFreshness
        mock_market.return_value = IranMarketPrice(
            platform="بازار ایران",
            title_fa="کالای تست",
            lowest_price_toman=None,
            average_price_toman=None,
            highest_price_toman=None,
            status="no_results",
            data_type=DataType.ESTIMATE,
            freshness=DataFreshness.UNAVAILABLE
        )
        
        result = agent_instance.analyze_product_comprehensive(
            product_query="قطعه خاص صنعتی بدون فروشگاه",
            custom_buy_price_cny=80.0
        )

        assert result["definite_profit_calculable"] is False
        assert result["insufficient_data"] is True
        prov = result["data_provenance"]
        assert prov["supplier_price_status"] == ComponentStatus.USER_MANUAL.value
        assert prov["iran_market_status"] == ComponentStatus.UNAVAILABLE.value
        assert prov["calculation_mode"] == "DISCOVERY_ONLY"
        assert any("قیمت فروش" in req for req in result["missing_requirements"])
        
        # Product discovery must remain 100% available
        assert result["regulations"]["primary_hs_code"].startswith("84") or result["regulations"]["primary_hs_code"].startswith("85")
        assert len(result["b2b_platforms"]) >= 9

def test_3_only_market_price_present(agent_instance):
    """
    Scenario 3: Only market price is present (e.g. from Digikala), but no buy price and no benchmark.
    Expectation: definite_profit_calculable is False, missing_requirements notes factory price,
    search links to Alibaba, 1688, AliExpress are all generated.
    """
    result = agent_instance.analyze_product_comprehensive(
        product_query="کالای آزمایشی ناشناخته بدون بنچمارک",
        custom_target_iran_price=1800000.0,
        include_indicative_benchmark=False
    )

    assert result["definite_profit_calculable"] is False
    assert result["insufficient_data"] is True
    prov = result["data_provenance"]
    assert prov["iran_market_status"] == ComponentStatus.USER_MANUAL.value
    assert prov["supplier_price_status"] == ComponentStatus.UNAVAILABLE.value
    assert prov["calculation_mode"] == "DISCOVERY_ONLY"
    assert any("خرید از چین" in req or "قیمت خرید" in req for req in result["missing_requirements"])
    assert "alibaba" in result["b2b_platforms"]
    assert "1688" in result["b2b_platforms"]
    assert "aliexpress" in result["b2b_platforms"]

def test_4_estimated_benchmark_prices(agent_instance):
    """
    Scenario 4: Sourcing uses indicative benchmark, market has price.
    Expectation: is_simulation is True, calculation_mode is SCENARIO_SIMULATION,
    scenarios are calculated under benchmark assumption, note clearly attached.
    """
    result = agent_instance.analyze_product_comprehensive(
        product_query="دریل شارژی",
        custom_target_iran_price=3200000.0,
        include_indicative_benchmark=True
    )

    assert result["is_simulation"] is True
    assert result["definite_profit_calculable"] is False
    assert result["insufficient_data"] is False
    prov = result["data_provenance"]
    assert prov["calculation_mode"] == "SCENARIO_SIMULATION"
    assert prov["supplier_price_status"] == ComponentStatus.ESTIMATED.value
    assert prov["supplier_price_value"] == 95.0  # Benchmarked drill price in CNY
    
    # Scenarios must be simulated
    assert result["sea_scenarios"]["is_sufficient_data"] is True
    assert result["sea_scenarios"]["realistic"]["net_profit_unit_toman"] > 0
    assert any("پیش‌فاکتور قطعی" in req for req in result["missing_requirements"])

def test_5_neither_price_available(agent_instance):
    """
    Scenario 5: Neither buy price nor sell price is available anywhere.
    Expectation: No fake profit produced, calculation_mode is DISCOVERY_ONLY,
    opportunity score is neutral (5.0), all statutory regulations & search links generated.
    """
    with patch.object(agent_instance.market_engine, "analyze_iran_market") as mock_market:
        from core.models import IranMarketPrice, DataFreshness
        mock_market.return_value = IranMarketPrice(
            platform="بازار ایران",
            title_fa="ناشناس",
            lowest_price_toman=None,
            average_price_toman=None,
            highest_price_toman=None,
            status="no_results",
            data_type=DataType.ESTIMATE,
            freshness=DataFreshness.UNAVAILABLE
        )
        
        result = agent_instance.analyze_product_comprehensive(
            product_query="کالای عجیب غیرقابل شناسایی xzy789",
            include_indicative_benchmark=False
        )

        assert result["insufficient_data"] is True
        assert result["sea_scenarios"]["realistic"] is None
        assert result["air_scenarios"]["realistic"] is None
        assert result["data_provenance"]["calculation_mode"] == "DISCOVERY_ONLY"
        assert result["opportunity_evaluation"]["opportunity_score"] == 0.0
        assert "اطلاعات برای محاسبه سود کافی نیست" in result["opportunity_evaluation"]["verdict"]
        
        # Regulatory information and links MUST NOT be hidden
        assert result["regulations"]["primary_hs_code"] != ""
        assert len(result["b2b_platforms"]) >= 10

def test_6_external_source_network_error(agent_instance):
    """
    Scenario 6: External source (Digikala API) throws an error (Timeout / 500).
    Expectation: System degrades gracefully without raising exception,
    logs notes, and returns discovery information.
    """
    with patch.object(agent_instance.market_engine.digikala_connector, "safe_get", return_value=None):
        iran_res = agent_instance.market_engine.analyze_iran_market("ایرپاد")
        assert iran_res.status == "no_results"
        assert iran_res.average_price_toman is None

        # Full analyze must not crash
        res = agent_instance.analyze_product_comprehensive("ایرپاد")
        assert "regulations" in res
        assert "b2b_platforms" in res

def test_7_external_source_empty_response(agent_instance):
    """
    Scenario 7: Digikala search returns 0 products.
    Expectation: System reports status unavailable without crashing or generating fake numbers.
    """
    with patch.object(agent_instance.market_engine.digikala_connector, "search") as mock_search:
        mock_search.return_value = {
            "status": ConnectorStatus.LIVE_VERIFIED,
            "query": "کالای نایاب",
            "products_count": 0,
            "products": [],
            "statistics": None,
            "notes": "استعلام بدون نتیجه"
        }
        
        iran_res = agent_instance.market_engine.analyze_iran_market("کالای نایاب")
        assert iran_res.status == "no_results"
        assert iran_res.active_sellers_count == 0

def test_8_search_with_different_name_or_specs(agent_instance):
    """
    Scenario 8: Product searched with different language / terms.
    User registered proforma with English title "TWS ANC Earbuds Pro".
    User searches with Persian keyword "هندزفری بلوتوث".
    Expectation: Multilingual database matching locates the proforma quote.
    """
    db = agent_instance.db
    # Insert a proforma in English
    db.save_manual_quote(
        search_id=None,
        name="Dongguan Audio Labs",
        platform="Alibaba Verified Supplier",
        title="TWS ANC Earbuds Pro Wireless 5.3",
        price_cny=32.0,
        moq=500,
        incoterms="FOB",
        source_url="https://www.alibaba.com/product/123"
    )

    # Search using Persian
    suppliers = agent_instance.sourcing_engine.search_suppliers(
        query="هندزفری بلوتوث",
        include_indicative_benchmark=False
    )

    assert len(suppliers) > 0
    found = suppliers[0]
    assert "Dongguan Audio Labs" in found.name or "TWS" in found.product_title
    assert found.unit_price_cny == 32.0
    assert found.data_type == DataType.MANUAL_QUOTE
