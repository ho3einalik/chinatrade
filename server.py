"""
FastAPI Server for China-to-Iran Import Intelligence & Arbitrage Agent.
Serves modern Dribbble-style UI and provides live search, sourcing and financial APIs.
"""

import os
import sys

# Ensure UTF-8 console output
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import webbrowser
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from config import CONFIG, TradeConfig
from core.agent import ChinaIranImportAgent
from core.report_generator import ReportGenerator

app = FastAPI(title="iTrade China-to-Iran Import Agent")

# اطمینان از وجود پوشه static و reports
os.makedirs("static", exist_ok=True)
os.makedirs("reports", exist_ok=True)

agent = ChinaIranImportAgent()
rep_gen = ReportGenerator()

class AnalyzeRequest(BaseModel):
    product: str
    target_price: Optional[float] = None
    quantity: Optional[int] = None
    category: Optional[str] = None

class ScanRequest(BaseModel):
    category: str
    min_margin: Optional[float] = 20.0

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/analyze")
async def analyze_endpoint(req: AnalyzeRequest):
    if not req.product.strip():
        raise HTTPException(status_code=400, detail="نام کالا نمی‌تواند خالی باشد.")
    
    report = agent.analyze_product(
        product_query=req.product,
        category=req.category,
        custom_target_iran_price=req.target_price,
        batch_quantity=req.quantity
    )
    return report.model_dump()

@app.post("/api/scan")
async def scan_endpoint(req: ScanRequest):
    opportunities = agent.find_opportunities(
        category=req.category,
        min_margin_percent=req.min_margin
    )
    return [op.model_dump() for op in opportunities]

@app.get("/api/download/{product_name}")
async def download_report_endpoint(product_name: str):
    report = agent.analyze_product(product_query=product_name)
    _, html_path = rep_gen.save_reports(report)
    return FileResponse(html_path, media_type="text/html", filename=f"dossier_{product_name}.html")

def launch_browser():
    try:
        # باز کردن مستقیم در مرورگر پیش‌فرض سیستم (کروم، اج)
        os.system("start http://localhost:8000")
    except Exception:
        webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    print("[*] در حال اجرای وب‌سرور مدرن روی http://localhost:8000...")
    launch_browser()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
