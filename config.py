"""
Configuration settings for China-to-Iran Import Intelligence & Arbitrage Agent.
Includes currency exchange rates, shipping tariffs, customs duties, and system settings.
"""

from dataclasses import dataclass
import os

@dataclass
class TradeConfig:
    # --- Currency Exchange Rates (in Iranian Toman) ---
    # Default realistic market rates (Can be adjusted via CLI / Web UI / Environment)
    RMB_TO_TOMAN: float = float(os.getenv("RMB_TO_TOMAN", "14200"))     # یوان چین به تومان
    USD_TO_TOMAN: float = float(os.getenv("USD_TO_TOMAN", "102000"))    # دلار آمریکا به تومان
    AED_TO_TOMAN: float = float(os.getenv("AED_TO_TOMAN", "27800"))     # درهم امارات به تومان

    # --- International Freight Rates (چین به ایران / دبی) ---
    # Air Cargo (هوایی - مناسب گجت‌ها، قطعات الکترونیک، نمونه‌ها)
    AIR_FREIGHT_USD_PER_KG: float = float(os.getenv("AIR_FREIGHT_USD_PER_KG", "12.0"))     # دلار به ازای هر کیلوگرم
    AIR_DELIVERY_DAYS_MIN: int = 7
    AIR_DELIVERY_DAYS_MAX: int = 14

    # Sea Freight LCL (دریایی خرده‌بار - مناسب بارهای حجیم، مواد پلیمری، ابزار)
    SEA_FREIGHT_USD_PER_CBM: float = float(os.getenv("SEA_FREIGHT_USD_PER_CBM", "110.0"))  # دلار به ازای هر متر مکعب (CBM)
    SEA_DELIVERY_DAYS_MIN: int = 25
    SEA_DELIVERY_DAYS_MAX: int = 40

    # Sea Freight FCL (کانتینر کامل 20 یا 40 فوت)
    CONTAINER_20FT_USD: float = float(os.getenv("CONTAINER_20FT_USD", "2200.0"))
    CONTAINER_40FT_USD: float = float(os.getenv("CONTAINER_40FT_USD", "3600.0"))

    # --- Customs Duties & Taxes in Iran (حقوق و عوارض گمرکی) ---
    DEFAULT_CUSTOMS_TARIFF_PERCENT: float = 4.0      # حقوق گمرکی پایه (معمولاً ۴ درصد)
    DEFAULT_COMMERCIAL_BENEFIT_PERCENT: float = 11.0 # میانگین سود بازرگانی (بسته به تعرفه بین ۱ تا ۴۰ درصد)
    VAT_PERCENT: float = 10.0                        # مالیات بر ارزش افزوده واردات (۱۰ درصد)
    CLEARANCE_BROKERAGE_PERCENT: float = 3.5         # کارمزد ترخیص‌کاری، ثبت سفارش، انبارداری و استاندارد
    DOMESTIC_LOGISTICS_PERCENT: float = 2.0          # حمل داخلی از بندرعباس/فرودگاه امام به انبار تهران

    # --- Telegram Bot Config ---
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # --- AI & Scraping Settings ---
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    REQUEST_TIMEOUT: int = 15

CONFIG = TradeConfig()
