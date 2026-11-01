"""
Configuration settings for China-to-Iran Import Intelligence & Arbitrage Agent.
Includes currency exchange rates, shipping tariffs, customs duties, and system settings.
All default rates are labeled as configured baselines and should be updated with live or manual inputs.
"""

from dataclasses import dataclass, field
import os

@dataclass
class TradeConfig:
    # --- Currency Exchange Rates (in Iranian Toman) ---
    # Baseline configured rates with provenance metadata
    RMB_TO_TOMAN: float = float(os.getenv("RMB_TO_TOMAN", "14200"))     # یوان چین به تومان
    USD_TO_TOMAN: float = float(os.getenv("USD_TO_TOMAN", "102000"))    # دلار آمریکا به تومان
    AED_TO_TOMAN: float = float(os.getenv("AED_TO_TOMAN", "27800"))     # درهم امارات به تومان
    
    FX_SOURCE_LABEL: str = "نرخ پایه پیکربندی‌شده (سامانه نظارت سنا / میانگین بازار حواله)"
    FX_LAST_UPDATED: str = "2026-03"

    # --- International Freight Rates (چین به ایران / دبی) ---
    AIR_FREIGHT_USD_PER_KG: float = float(os.getenv("AIR_FREIGHT_USD_PER_KG", "12.0"))     # دلار به ازای هر کیلوگرم (پیش‌فاکتور کارگو)
    AIR_DELIVERY_DAYS_MIN: int = 7
    AIR_DELIVERY_DAYS_MAX: int = 14

    SEA_FREIGHT_USD_PER_CBM: float = float(os.getenv("SEA_FREIGHT_USD_PER_CBM", "110.0"))  # دلار به ازای هر متر مکعب (CBM)
    SEA_DELIVERY_DAYS_MIN: int = 25
    SEA_DELIVERY_DAYS_MAX: int = 40

    CONTAINER_20FT_USD: float = float(os.getenv("CONTAINER_20FT_USD", "2200.0"))
    CONTAINER_40FT_USD: float = float(os.getenv("CONTAINER_40FT_USD", "3600.0"))

    # --- Customs Duties & Taxes in Iran (حقوق و عوارض گمرکی) ---
    DEFAULT_CUSTOMS_TARIFF_PERCENT: float = 4.0      # حقوق گمرکی پایه
    DEFAULT_COMMERCIAL_BENEFIT_PERCENT: float = 11.0 # سود بازرگانی میانگین
    VAT_PERCENT: float = 10.0                        # مالیات بر ارزش افزوده واردات
    CLEARANCE_BROKERAGE_PERCENT: float = 4.5         # کارمزد ترخیص‌کاری و خدمات بازرگانی
    DOMESTIC_LOGISTICS_PERCENT: float = 3.0          # حمل داخلی به انبار مقصد

    # --- System & Safety Mode ---
    ALLOW_DEMO_DATA: bool = os.getenv("ALLOW_DEMO_DATA", "false").lower() in ("true", "1", "yes")

    # --- Telegram Bot Config ---
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # --- Scraping & HTTP Settings ---
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    REQUEST_TIMEOUT: int = 10

CONFIG = TradeConfig()
