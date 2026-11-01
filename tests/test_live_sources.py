"""
Live network integration tests for external sources (Digikala, China B2B platforms).
Run explicitly with:
    pytest -m live
Skip in CI/offline with:
    pytest -m "not live"
"""

import pytest
from connectors.digikala import DigikalaConnector
from connectors.china_b2b import ChinaB2BConnector
from connectors.base import ConnectorStatus

@pytest.mark.live
def test_digikala_live_search_or_graceful_fallback():
    connector = DigikalaConnector()
    # Search for an ubiquitous term like "ساعت هوشمند"
    result = connector.search("ساعت هوشمند", page=1)
    
    assert "status" in result
    assert "query" in result
    assert result["query"] == "ساعت هوشمند"
    
    # If network is reachable, it should be LIVE_VERIFIED and contain products
    # If network/proxy/firewall blocks it, it must return MANUAL_FALLBACK without crashing
    if result["status"] == ConnectorStatus.LIVE_VERIFIED:
        assert result["products_count"] >= 0
        if result["products"]:
            first = result["products"][0]
            assert "id" in first
            assert "price_toman" in first
            assert first["price_toman"] > 0
            assert "url" in first
    else:
        assert result["status"] == ConnectorStatus.MANUAL_FALLBACK
        assert "دیجی‌کالا" in result["notes"]

@pytest.mark.live
def test_china_b2b_live_links_generation():
    connector = ChinaB2BConnector()
    links = connector.generate_search_links("TWS ANC Earbuds")

    # Verify all major platforms have structured descriptors
    for plat in ["ehsy", "gongchang", "makepolo", "1688", "chemnet"]:
        assert plat in links
        assert "url" in links[plat]
        assert "status" in links[plat]
        assert "name" in links[plat]
        assert links[plat]["url"].startswith("http")
