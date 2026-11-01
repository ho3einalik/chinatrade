import pytest
from fastapi.testclient import TestClient
from server import app
from core.db import Database

client = TestClient(app)

def test_root_serves_html():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "iTrade Enterprise" in resp.text

def test_api_analyze_insufficient_data_flow():
    """
    Verifies that querying an unknown product without proforma quotes
    honestly returns insufficient_data=True and does NOT fabricate profits.
    """
    resp = client.post("/api/analyze", json={
        "product": "کالای تستی بدون تامین‌کننده مشخص",
        "category": "عمومی",
        "allow_demo": False
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["query"] == "کالای تستی بدون تامین‌کننده مشخص"
    assert "report" in data
    assert data["report"]["insufficient_data"] is True
    assert data["sea_scenarios"]["is_sufficient_data"] is False
    assert data["sea_scenarios"]["realistic"] is None
    assert data["sea_scenarios"]["optimistic"] is None
    assert data["sea_scenarios"]["pessimistic"] is None
    assert data["report"]["opportunity_score"] <= 1.5

def test_api_analyze_with_demo_or_quote_calculation():
    """
    Verifies that when demo is explicitly allowed or a quote exists,
    the 3 financial scenarios (Realistic, Optimistic, Pessimistic) are accurately computed.
    """
    resp = client.post("/api/analyze", json={
        "product": "ساعت هوشمند اولترا",
        "category": "گجت‌ها و الکترونیک مصرفی",
        "allow_demo": True
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["query"] == "ساعت هوشمند اولترا"
    assert "report" in data
    assert "air_scenarios" in data
    assert "sea_scenarios" in data
    assert data["snapshot_id"] > 0

    scen = data["sea_scenarios"]
    assert "realistic" in scen
    assert "optimistic" in scen
    assert "pessimistic" in scen
    assert scen["realistic"]["landed_cost_unit_toman"] > 0
    assert scen["pessimistic"]["landed_cost_unit_toman"] > scen["realistic"]["landed_cost_unit_toman"]
    assert scen["optimistic"]["net_profit_unit_toman"] > scen["realistic"]["net_profit_unit_toman"]

def test_ssrf_protection_blocks_internal_and_dns_rebinding():
    # 1. Direct loopback
    resp_loopback = client.post("/api/analyze", json={"product": "http://127.0.0.1:8000/admin"})
    assert resp_loopback.status_code == 400
    assert "ورودی نامعتبر" in resp_loopback.json()["detail"]

    # 2. AWS/Cloud metadata IP
    resp_metadata = client.post("/api/analyze", json={"product": "http://169.254.169.254/latest/meta-data"})
    assert resp_metadata.status_code == 400
    assert "ورودی نامعتبر" in resp_metadata.json()["detail"]

    # 3. Localhost hostname
    resp_host = client.post("/api/analyze", json={"product": "http://localhost:8000/internal"})
    assert resp_host.status_code == 400

    # 4. Private RFC1918 subnet
    resp_priv = client.post("/api/analyze", json={"product": "http://192.168.1.1/router"})
    assert resp_priv.status_code == 400

def test_manual_market_price_entry():
    resp = client.post("/api/manual-market-price", json={
        "product_title": "ساعت هوشمند اولترا",
        "platform": "بازار چارسو تهران",
        "price_toman": 1450000,
        "source_url": "https://charsou.example/store"
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

def test_manual_quote_and_csv_upload():
    # 1. Manual Quote
    resp_quote = client.post("/api/manual-quote", json={
        "supplier_name": "Shenzhen Factory Pro",
        "product_title": "Smart Watch Ultra 2",
        "unit_price_cny": 48.0,
        "moq": 300
    })
    assert resp_quote.status_code == 200
    assert resp_quote.json()["status"] == "success"

    # 2. CSV Upload
    csv_payload = b"name,product_title,unit_price_cny,moq\nFactory A,Watch Model A,35.0,500\nFactory B,Watch Model B,42.0,200\n"
    resp_csv = client.post(
        "/api/upload-csv",
        files={"file": ("quotes.csv", csv_payload, "text/csv")}
    )
    assert resp_csv.status_code == 200
    assert resp_csv.json()["imported_count"] == 2

def test_price_alerts_and_history():
    # 1. Create alert
    resp_alert = client.post("/api/alerts", json={
        "product_name": "ساعت هوشمند",
        "threshold_profit_toman": 100000.0,
        "user_contact": "importer@example.com"
    })
    assert resp_alert.status_code == 200
    assert resp_alert.json()["alert_id"] > 0

    # 2. Get history
    resp_hist = client.get("/api/history")
    assert resp_hist.status_code == 200
    assert isinstance(resp_hist.json(), list)

def test_report_downloads():
    # HTML download
    resp_html = client.get("/api/download/html/ساعت هوشمند")
    assert resp_html.status_code == 200
    assert resp_html.headers["content-type"].startswith("text/html")

    # CSV download
    resp_csv = client.get("/api/download/csv/ساعت هوشمند")
    assert resp_csv.status_code == 200
    assert resp_csv.headers["content-type"].startswith("text/csv")

    # Markdown download
    resp_md = client.get("/api/download/md/ساعت هوشمند")
    assert resp_md.status_code == 200
    assert resp_md.headers["content-type"].startswith("text/markdown")
