"""
FastAPI Server for China-to-Iran Import Intelligence & Arbitrage Agent.
Includes deep SSRF Protection with DNS resolution, 3-Scenario Profit Modeling,
Matching Breakdown, Supplier Audits, Historical Snapshots, CSV/Manual Import, and Price Alerts.
"""

import os
import sys
import socket
import ipaddress
import urllib.parse
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
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
from core.models import DataType

app = FastAPI(title="iTrade China Enterprise API", version="2.1.0")

os.makedirs("static", exist_ok=True)
os.makedirs("reports", exist_ok=True)

agent = ChinaIranImportAgent()
rep_gen = ReportGenerator()
db = Database()

# --- Deep SSRF Protection with DNS Resolution ---
FORBIDDEN_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),       # RFC 1918 Private
    ipaddress.ip_network("172.16.0.0/12"),    # RFC 1918 Private
    ipaddress.ip_network("192.168.0.0/16"),   # RFC 1918 Private
    ipaddress.ip_network("169.254.0.0/16"),   # Link-Local & Cloud Metadata (AWS, GCP, Azure)
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
    ipaddress.ip_network("::1/128"),          # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),        # IPv6 Link-Local
]

def is_ip_forbidden(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_unspecified or ip_obj.is_reserved:
        return True
    for net in FORBIDDEN_NETWORKS:
        if ip_obj in net:
            return True
    return False

def validate_safe_target(target: str) -> bool:
    """
    Deep SSRF verification:
    1. Only allows http and https schemes if a URL is provided.
    2. Resolves DNS to all IP addresses and ensures NONE of them are private/loopback/metadata.
    """
    clean_target = target.strip()
    if not clean_target:
        return True

    # Check if target is a URL or IP
    if "://" in clean_target:
        parsed = urllib.parse.urlparse(clean_target)
        if parsed.scheme.lower() not in ("http", "https"):
            return False
        hostname = parsed.hostname
    elif any(c in clean_target for c in ("/", ":", "?", "@")):
        # Could be an IP or host with port
        hostname = clean_target.split("/")[0].split(":")[0]
    else:
        # Plain product query (e.g. "ساعت هوشمند") - safe text
        return True

    if not hostname:
        return True

    # Direct IP string check
    try:
        ip = ipaddress.ip_address(hostname)
        if is_ip_forbidden(ip):
            return False
    except ValueError:
        # Hostname resolution check (Protects against DNS rebinding e.g. 127.0.0.1.nip.io)
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                sockaddr = item[4]
                resolved_ip_str = sockaddr[0]
                resolved_ip = ipaddress.ip_address(resolved_ip_str)
                if is_ip_forbidden(resolved_ip):
                    return False
        except socket.gaierror:
            pass  # Unresolvable domain

    return True

# --- Request Models ---
class AnalyzeRequest(BaseModel):
    product: str
    target_price: Optional[float] = None
    quantity: Optional[int] = None
    category: Optional[str] = None
    allow_demo: Optional[bool] = False

class ManualQuoteRequest(BaseModel):
    supplier_name: str
    platform: str = "Manual / Proforma Invoice"
    product_title: str
    unit_price_cny: float
    moq: int = 100
    incoterms: str = "EXW"
    source_url: str = ""
    weight_kg: float = 0.2
    volume_cbm: float = 0.001
    search_id: Optional[int] = None

class ManualMarketPriceRequest(BaseModel):
    product_title: str
    platform: str
    price_toman: float
    source_url: str = ""

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
    
    if not validate_safe_target(clean_product):
        raise HTTPException(status_code=400, detail="ورودی نامعتبر یا آدرس شبکه داخلی/لوپ‌بک (SSRF Forbidden) شناسایی شد.")

    result = agent.analyze_product_comprehensive(
        product_query=clean_product,
        category=req.category,
        custom_target_iran_price=req.target_price,
        batch_quantity=req.quantity,
        allow_demo=bool(req.allow_demo)
    )
    return result

@app.post("/api/manual-quote")
async def manual_quote_endpoint(req: ManualQuoteRequest):
    if req.unit_price_cny <= 0:
        raise HTTPException(status_code=400, detail="قیمت یوان باید بیشتر از صفر باشد.")
    
    if req.source_url and not validate_safe_target(req.source_url):
        raise HTTPException(status_code=400, detail="آدرس لینک منبع نامعتبر یا ناامن است.")

    quote_id = db.save_manual_quote(
        search_id=req.search_id,
        name=req.supplier_name.strip(),
        platform=req.platform.strip(),
        title=req.product_title.strip(),
        price_cny=req.unit_price_cny,
        moq=req.moq,
        incoterms=req.incoterms.upper(),
        source_url=req.source_url.strip(),
        data_type=DataType.MANUAL_QUOTE.value
    )
    return {"status": "success", "quote_id": quote_id, "message": "پیش‌فاکتور با موفقیت در پایگاه داده ثبت شد."}

@app.post("/api/manual-market-price")
async def manual_market_price_endpoint(req: ManualMarketPriceRequest):
    if req.price_toman <= 0:
        raise HTTPException(status_code=400, detail="قیمت تومان باید بیشتر از صفر باشد.")

    db.record_market_price(
        title=req.product_title.strip(),
        platform=req.platform.strip(),
        price_toman=req.price_toman,
        source_url=req.source_url.strip(),
        data_type=DataType.MANUAL_QUOTE.value
    )
    return {"status": "success", "message": "قیمت بازار ایران با موفقیت ثبت شد."}

@app.post("/api/upload-csv")
async def upload_csv_endpoint(file: UploadFile = File(...)):
    # Limit max upload size to 5MB
    MAX_CSV_SIZE = 5 * 1024 * 1024
    contents = await file.read()
    if len(contents) > MAX_CSV_SIZE:
        raise HTTPException(status_code=413, detail="حجم فایل ارسالی بیش از ۵ مگابایت است.")

    try:
        text = contents.decode("utf-8")
    except UnicodeDecodeError:
        text = contents.decode("latin-1")

    suppliers = ManualQuotationParser.parse_csv_content(text)
    if not suppliers:
        raise HTTPException(status_code=400, detail="هیچ رکورد معتبری در فایل CSV یافت نشد.")

    saved_count = 0
    for s in suppliers:
        db.save_manual_quote(
            search_id=None,
            name=s.name,
            platform=s.platform,
            title=s.product_title,
            price_cny=s.unit_price_cny,
            moq=s.moq,
            incoterms=s.incoterms.value if hasattr(s, "incoterms") else "EXW",
            source_url=s.source_url,
            data_type=DataType.CSV_IMPORT.value
        )
        saved_count += 1

    return {"status": "success", "imported_count": saved_count, "message": f"{saved_count} تأمین‌کننده واقعی از فایل CSV با موفقیت وارد شدند."}

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
    real_path = os.path.abspath(html_path)
    if not real_path.startswith(os.path.abspath("reports")):
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز به فایل.")
    return FileResponse(html_path, media_type="text/html", filename=f"itrade_{clean_name}.html")

@app.get("/api/download/csv/{product_name}")
async def download_csv_report(product_name: str):
    clean_name = os.path.basename(product_name.strip())
    report = agent.analyze_product(product_query=clean_name)
    _, _, csv_path = rep_gen.save_reports(report)
    real_path = os.path.abspath(csv_path)
    if not real_path.startswith(os.path.abspath("reports")):
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز به فایل.")
    return FileResponse(csv_path, media_type="text/csv", filename=f"itrade_{clean_name}.csv")

@app.get("/api/download/md/{product_name}")
async def download_md_report(product_name: str):
    clean_name = os.path.basename(product_name.strip())
    report = agent.analyze_product(product_query=clean_name)
    md_path, _, _ = rep_gen.save_reports(report)
    real_path = os.path.abspath(md_path)
    if not real_path.startswith(os.path.abspath("reports")):
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز به فایل.")
    return FileResponse(md_path, media_type="text/markdown", filename=f"itrade_{clean_name}.md")

if __name__ == "__main__":
    print("[*] در حال اجرای وب‌سرور مدرن روی http://localhost:8000...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
