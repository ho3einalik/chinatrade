"""
FastAPI Server for China-to-Iran Import Intelligence & Arbitrage Agent.
Includes SSRF Protection, 3-Scenario Profit Modeling, Matching Breakdown,
Supplier Audits, Historical Snapshots, CSV/Manual Import, and Price Alerts.
"""

import os
import sys
import ipaddress
import urllib.parse
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

# Ensure UTF-8 console output
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config import CONFIG, TradeConfig
from core.agent import ChinaIranImportAgent
from core.report_generator import ReportGenerator
from core.db import Database
from connectors.manual_entry import ManualQuotationParser

app = FastAPI(title="iTrade China Enterprise API", version="2.0.0")

os.makedirs("static", exist_ok=True)
os.makedirs("reports", exist_ok=True)

agent = ChinaIranImportAgent()
rep_gen = ReportGenerator()
db = Database()

# --- SSRF Protection Utility ---
def validate_safe_url(url: str) -> bool:
    """Validates that a URL does not point to internal/private networks or loopback."""
    try:
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return True  # Empty is fine or relative

        if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            return False

        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False
        except ValueError:
            pass  # Hostname is a domain name, not raw IP

        return True
    except Exception:
        return False

# --- Request Models ---
class AnalyzeRequest(BaseModel):
    product: str
    target_price: Optional[float] = None
    quantity: Optional[int] = None
    category: Optional[str] = None

class ManualQuoteRequest(BaseModel):
    supplier_name: str
    platform: str = "Manual / Proforma Invoice"
    product_title: str
    unit_price_cny: float
    moq: int = 100
    weight_kg: float = 0.2
    volume_cbm: float = 0.001
    search_id: Optional[int] = None

class AlertRequest(BaseModel):
    product_name: str
    threshold_profit_toman: float
    user_contact: str

# --- Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/analyze")
async def analyze_endpoint(req: AnalyzeRequest):
    clean_product = req.product.strip()
    if not clean_product:
        raise HTTPException(status_code=400, detail="نام کالا نمی‌تواند خالی باشد.")
    
    # SSRF check on input
    if not validate_safe_url(clean_product):
        raise HTTPException(status_code=400, detail="ورودی نامعتبر یا آدرس شبکه داخلی شناسایی شد.")

    result = agent.analyze_product_comprehensive(
        product_query=clean_product,
        category=req.category,
        custom_target_iran_price=req.target_price,
        batch_quantity=req.quantity
    )
    return result

@app.post("/api/manual-quote")
async def manual_quote_endpoint(req: ManualQuoteRequest):
    if req.unit_price_cny <= 0:
        raise HTTPException(status_code=400, detail="قیمت یوان باید بیشتر از صفر باشد.")
    
    quote_id = db.save_manual_quote(
        search_id=req.search_id,
        name=req.supplier_name,
        platform=req.platform,
        title=req.product_title,
        price_cny=req.unit_price_cny,
        moq=req.moq
    )
    return {"status": "success", "quote_id": quote_id, "message": "پیش‌فاکتور با موفقیت ذخیره شد."}

@app.post("/api/upload-csv")
async def upload_csv_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        text = contents.decode("utf-8")
    except UnicodeDecodeError:
        text = contents.decode("latin-1")

    suppliers = ManualQuotationParser.parse_csv_content(text)
    if not suppliers:
        raise HTTPException(status_code=400, detail="هیچ رکورد معتبری در فایل CSV یافت نشد.")

    saved_count = 0
    for s in suppliers:
        db.save_manual_quote(None, s.name, s.platform, s.product_title, s.unit_price_cny, s.moq)
        saved_count += 1

    return {"status": "success", "imported_count": saved_count, "message": f"{saved_count} تأمین‌کننده با موفقیت وارد شدند."}

@app.get("/api/history")
async def get_history_endpoint(limit: int = 10):
    return db.get_recent_snapshots(limit=limit)

@app.get("/api/snapshot/{snapshot_id}")
async def get_snapshot_endpoint(snapshot_id: int):
    snap = db.get_snapshot_by_id(snapshot_id)
    if not snap:
        raise HTTPException(status_code=404, detail="اسنپ‌شات یافت نشد.")
    return snap

@app.post("/api/alerts")
async def create_alert_endpoint(req: AlertRequest):
    alert_id = db.create_price_alert(
        product_name=req.product_name,
        threshold_profit_toman=req.threshold_profit_toman,
        user_contact=req.user_contact
    )
    return {"status": "success", "alert_id": alert_id, "message": "هشدار قیمت و سودآوری با موفقیت ثبت شد."}

@app.get("/api/alerts")
async def get_alerts_endpoint():
    return db.get_active_alerts()

@app.get("/api/download/html/{product_name}")
async def download_html_report(product_name: str):
    clean_name = os.path.basename(product_name.strip())
    report = agent.analyze_product(product_query=clean_name)
    _, html_path, _ = rep_gen.save_reports(report)
    return FileResponse(html_path, media_type="text/html", filename=f"itrade_{clean_name}.html")

@app.get("/api/download/csv/{product_name}")
async def download_csv_report(product_name: str):
    clean_name = os.path.basename(product_name.strip())
    report = agent.analyze_product(product_query=clean_name)
    _, _, csv_path = rep_gen.save_reports(report)
    return FileResponse(csv_path, media_type="text/csv", filename=f"itrade_{clean_name}.csv")

@app.get("/api/download/md/{product_name}")
async def download_md_report(product_name: str):
    clean_name = os.path.basename(product_name.strip())
    report = agent.analyze_product(product_query=clean_name)
    md_path, _, _ = rep_gen.save_reports(report)
    return FileResponse(md_path, media_type="text/markdown", filename=f"itrade_{clean_name}.md")

if __name__ == "__main__":
    print("[*] در حال اجرای وب‌سرور مدرن روی http://localhost:8000...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
