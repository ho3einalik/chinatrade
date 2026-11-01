"""
Integration tests for FastAPI endpoints under /api/trade-hub.
"""

import pytest
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def test_api_trade_sources():
    response = client.get("/api/trade-hub/sources")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 7
    source_ids = [s["source_id"] for s in data]
    assert "trademap" in source_ids
    assert "comtrade" in source_ids
    assert "tpo_iran" in source_ids


def test_api_trade_source_links():
    response = client.get("/api/trade-hub/sources/search-links?hs_code=2713.20&country=Iraq&product_name=Bitumen")
    assert response.status_code == 200
    data = response.json()
    links = data["links"]
    assert "itc_trade_map" in links
    assert "un_comtrade" in links
    assert "iran_iraq_chamber" in links


def test_api_network_contacts_crud():
    contact_payload = {
        "name": "API Test Importer Corp",
        "country": "Iraq",
        "city": "Basra",
        "role": "BUYER",
        "email": "test_api_importer@basra.iq",
        "products": ["Cement", "Ceramic Tiles"],
        "unit_price_usd": 75.0,
        "payment_terms": "L/C at sight"
    }
    # Create contact
    res_post = client.post("/api/trade-hub/network/contacts", json=contact_payload)
    assert res_post.status_code in [200, 400]  # May already exist if rerun

    # List contacts
    res_get = client.get("/api/trade-hub/network/contacts?query=Cement")
    assert res_get.status_code == 200
    data = res_get.json()
    assert isinstance(data, list)


def test_api_seller_journey():
    payload = {
        "product_name": "قیر ۶۰/۷۰",
        "origin_country": "Iran",
        "target_country": "India",
        "unit_cost_usd": 380.0,
        "batch_quantity": 500
    }
    response = client.post("/api/trade-hub/journey/seller", json=payload)
    assert response.status_code == 200
    dossier = response.json()
    assert dossier["hs_code_primary"] == "2713.20"
    assert len(dossier["top_importing_countries"]) > 0
    assert len(dossier["action_roadmap"]) > 0


def test_api_buyer_journey():
    payload = {
        "product_name": "پلی‌اتیلن سنگین HDPE",
        "origin_country_preference": "Turkey",
        "destination_country": "Iran",
        "batch_quantity": 100
    }
    response = client.post("/api/trade-hub/journey/buyer", json=payload)
    assert response.status_code == 200
    dossier = response.json()
    assert dossier["destination_country"] == "Iran"
    assert dossier["estimated_landed_cost"] is not None


def test_api_discovery_journey():
    response = client.get("/api/trade-hub/journey/discovery?sector=petrochemicals&min_growth_pct=4.0")
    assert response.status_code == 200
    dossier = response.json()
    assert len(dossier["discovered_opportunities"]) > 0
    assert len(dossier["untapped_export_potential_markets"]) > 0


def test_api_calculate_cost():
    payload = {
        "origin_country": "Iran",
        "destination_country": "Iraq",
        "incoterms": "FOB",
        "trade_direction": "EXPORT",
        "batch_quantity": 200,
        "purchase_cost_per_unit_usd": 410.0,
        "target_selling_price_per_unit_usd": 590.0
    }
    response = client.post("/api/trade-hub/calculate-cost", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert float(result["total_landed_cost_batch_usd"]) > 0
    assert float(result["net_profit_per_unit_usd"]) > 0
    assert len(result["line_items"]) == 9
