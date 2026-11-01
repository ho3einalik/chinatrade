"""
Unit and Integration tests for Iran Domestic Buyer & Consuming Industry Engine.
Tests commodity parsing, Iranian off-taker matching, batch domestic valuation,
logistics estimation, and API integration.
"""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from trade_hub.intelligence.domestic_buyers import IranDomesticBuyerEngine
from trade_hub.intelligence.journey_seller import SellerJourneyEngine
from server import app

client = TestClient(app)


def test_parse_commodity_query():
    # Persian numbers and keywords
    prod, qty, unit = IranDomesticBuyerEngine.parse_commodity_query("۳۰۰۰ تن جو دارم")
    assert prod == "جو"
    assert qty == Decimal("3000")
    assert unit == "تن"

    # English / Arabic numbers
    prod, qty, unit = IranDomesticBuyerEngine.parse_commodity_query("5000 ton corn")
    assert "corn" in prod.lower() or "ذرت" in prod
    assert qty == Decimal("5000")

    # Plain commodity name without quantity
    prod, qty, unit = IranDomesticBuyerEngine.parse_commodity_query("میلگرد آجدار")
    assert "میلگرد" in prod
    assert qty is None


def test_match_barley_domestic_buyers():
    result = IranDomesticBuyerEngine.match_domestic_buyers(
        product_query="3000 تن جو دارم",
        quantity=Decimal("3000"),
        unit_name="تن"
    )

    assert result["is_domestic_focus"] is True
    assert result["commodity_name"] == "جو دامی و خوراکی"
    assert result["hs_code"] == "1003.90"
    assert result["total_volume_tons"] == Decimal("3000")
    assert result["trucks_needed"] == 125  # 3000 / 24 rounded up
    assert result["unit_price_toman_kg"] == Decimal("12500")
    assert result["total_valuation_toman"] == Decimal("37500000000")  # 37.5 Billion Tomans
    assert result["total_valuation_irr"] == Decimal("375000000000")

    # Consuming industries
    industries = result["consuming_industries"]
    assert len(industries) >= 3
    feed_mill = next((i for i in industries if "خوراک" in i["industry_name"]), None)
    assert feed_mill is not None
    assert feed_mill["share_pct"] == 65

    # Domestic Buyers
    buyers = result["domestic_buyers"]
    assert len(buyers) >= 5
    # Check top buyers
    names = [b.entity_name for b in buyers]
    assert any("پارس" in n for n in names)
    assert any("مغان" in n for n in names)
    assert any("دامداران" in n for n in names)

    # Check buyer attributes
    b0 = buyers[0]
    assert b0.buyer_type is not None
    assert b0.city_province is not None
    assert b0.purchasing_capacity is not None
    assert b0.payment_terms_expected is not None
    assert b0.contact_channel is not None

    # Check formal sales letter
    assert "پیشنهاد رسمی فروش" in result["draft_sales_offer_fa"]
    assert "3,000" in result["draft_sales_offer_fa"] or "3000" in result["draft_sales_offer_fa"]


def test_seller_journey_domestic_flow():
    engine = SellerJourneyEngine()
    dossier = engine.execute(
        product_name="۳۰۰۰ تن جو دامی دارم برای فروش داخل ایران",
        origin_country="Iran",
        target_country="Iran"
    )

    assert dossier.product_name_fa == "جو دامی و خوراکی"
    assert dossier.hs_code_primary == "1003.90"
    assert dossier.domestic_market_summary is not None
    assert len(dossier.domestic_buyers) >= 5
    assert dossier.domestic_market_summary["total_valuation_toman"] == Decimal("37500000000")
    assert "پیشنهاد رسمی فروش" in dossier.draft_sales_pitch_fa


def test_api_seller_journey_domestic_endpoint():
    payload = {
        "product_name": "3000 تن جو دارم",
        "origin_country": "Iran",
        "target_country": "Iran",
        "batch_quantity": 3000,
        "unit_name": "Tons"
    }
    response = client.post("/api/trade-hub/journey/seller", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["hs_code_primary"] == "1003.90"
    assert "domestic_market_summary" in data
    dom_summary = data["domestic_market_summary"]
    assert int(dom_summary["total_valuation_toman"]) == 37500000000
    assert dom_summary["trucks_needed"] == 125
    assert len(dom_summary["consuming_industries"]) >= 3
    assert len(data["domestic_buyers"]) >= 5
    assert any("پارس" in b["entity_name"] for b in data["domestic_buyers"])
