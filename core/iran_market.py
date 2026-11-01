"""
Iran Market Intelligence Engine.
Performs live queries against Digikala API, extracts robust pricing statistics,
and generates direct search links for Iranian distribution channels:
- Digikala (مارکت‌پلیس سراسری - استعلام زنده واقعی)
- Torob (موتور مقایسه ۱۰,۰۰۰ فروشگاه اینترنتی - لینک جستجوی عمیق)
- Emalls (ایمالز - مرجع قیمت کالاهای رسمی - لینک جستجوی عمیق)
- Basalam (باسلام - غرفه‌داران و واردکنندگان - لینک جستجوی عمیق)
- Divar / Sheypoor (معاملات نقدی بازار آزاد - لینک جستجوی عمیق)

قانون اصالت داده: هیچ قیمت تخمینی با ضرایب ثابت (مانند ضرب در ۱.۰۳) تولید نمی‌شود.
در صورت عدم دسترسی به قیمت قطعی، وضعیت unavailable ثبت شده و لینک جستجوی مستقیم ارائه می‌شود.
"""

from typing import Optional, Dict, Any, List
import urllib.parse
from datetime import datetime, timezone
import logging

from connectors.digikala import DigikalaConnector
from core.models import IranMarketPrice, IranMarketChannel, DataType, DataFreshness

logger = logging.getLogger("iran_market")

class IranMarketEngine:
    def __init__(self, db=None):
        self.db = db
        self.digikala_connector = DigikalaConnector()

    def analyze_iran_market(
        self,
        query: str,
        custom_target_price: Optional[float] = None
    ) -> IranMarketPrice:
        """
        تحلیل و استخراج قیمت‌های واقعی کالا در بازار ایران:
        ۱. استعلام زنده API از دیجی‌کالا
        ۲. بررسی قیمت‌های دستی ثبت‌شده توسط کاربر در دیتابیس
        ۳. ارائه لینک‌های مستقیم استعلام در ترب، ایمالز، باسلام و دیوار
        ۴. در صورت نبود قیمت زنده یا دستی، مقدار قیمت‌ها None بازگردانده شده و وضعیت no_results ثبت می‌شود.
        """
        encoded_q = urllib.parse.quote(query)
        torob_url = f"https://torob.com/search/?query={encoded_q}"
        emalls_url = f"https://emalls.ir/search/{encoded_q}"
        basalam_url = f"https://basalam.com/search?q={encoded_q}"
        divar_url = f"https://divar.ir/s/tehran?q={encoded_q}"
        digikala_url = f"https://www.digikala.com/search/?q={encoded_q}"

        # ۱. استعلام زنده از دیجی‌کالا
        live_result = self.digikala_connector.search(query)
        has_live_data = live_result.get("status") == "LIVE_VERIFIED" and live_result.get("products_count", 0) > 0

        now_utc = datetime.now(timezone.utc).isoformat()

        if has_live_data:
            stats = live_result.get("statistics") or {}
            lowest = float(stats.get("min_toman", 0))
            avg = float(stats.get("trimmed_mean_toman") or stats.get("median_toman", 0))
            highest = float(stats.get("max_toman", 0))
            sellers_count = live_result.get("products_count", 0)
            sample_products = live_result.get("products", [])[:5]
            status = "available"
            title_fa = sample_products[0]["title_fa"] if sample_products else query
            data_type = DataType.LIVE_API
            freshness = DataFreshness.FRESH
            velocity = min(max(sellers_count // 3, 6), 10)
        elif custom_target_price and custom_target_price > 0:
            # کاربر دستی قیمت فروش هدف وارد کرده است
            lowest = float(custom_target_price)
            avg = float(custom_target_price)
            highest = float(custom_target_price)
            sellers_count = 1
            sample_products = []
            status = "manual_override"
            title_fa = query
            data_type = DataType.MANUAL_QUOTE
            freshness = DataFreshness.FRESH
            velocity = 6
        else:
            # هیچ استعلام زنده‌ای موجود نیست و قیمت دستی هم داده نشده
            lowest = None
            avg = None
            highest = None
            sellers_count = 0
            sample_products = []
            status = "no_results"
            title_fa = query
            data_type = DataType.ESTIMATE
            freshness = DataFreshness.UNAVAILABLE
            velocity = 5

        # ۲. بررسی قیمت‌های دستی ثبت‌شده در پایگاه داده
        manual_prices = {}
        if self.db:
            try:
                rec_prices = self.db.get_latest_market_prices(query)
                for rp in rec_prices:
                    manual_prices[rp["platform"].lower()] = float(rp["price_toman"])
            except Exception:
                pass

        # ۳. ساخت کانال‌های بازار ایران با صداقت کامل
        # فقط دیجی‌کالا در صورت پاسخ واقعی زنده تلقی می‌شود؛ بقیه لینک‌های جستجوی مستقیم هستند مگر اینکه کاربر دستی قیمت داده باشد.
        channels: List[IranMarketChannel] = [
            IranMarketChannel(
                name="دیجی‌کالا (Digikala)",
                price_toman=avg if has_live_data else (custom_target_price or None),
                price_label="استعلام زنده موجودی و قیمت فروشگاه‌ها" if has_live_data else "استعلام زنده ناموفق یا بدون نتیجه",
                url=digikala_url,
                is_live=has_live_data,
                data_type=DataType.LIVE_API if has_live_data else (DataType.MANUAL_QUOTE if custom_target_price else DataType.ESTIMATE),
                channel_type="live_api",
                fetch_time_utc=now_utc if has_live_data else None
            ),
            IranMarketChannel(
                name="ترب (Torob - مقایسه ۱۰,۰۰۰ فروشگاه)",
                price_toman=manual_prices.get("torob"),
                price_label="قیمت ثبت‌شده توسط کاربر" if "torob" in manual_prices else "لینک جستجوی مستقیم (ضدربات ترب خزش خودکار را مسدود می‌کند)",
                url=torob_url,
                is_live=False,
                data_type=DataType.MANUAL_QUOTE if "torob" in manual_prices else DataType.ESTIMATE,
                channel_type="search_link",
                fetch_time_utc=now_utc if "torob" in manual_prices else None
            ),
            IranMarketChannel(
                name="ایمالز (Emalls - مقایسه قیمت فروشگاه‌ها)",
                price_toman=manual_prices.get("emalls"),
                price_label="قیمت ثبت‌شده توسط کاربر" if "emalls" in manual_prices else "لینک جستجوی مستقیم ایمالز",
                url=emalls_url,
                is_live=False,
                data_type=DataType.MANUAL_QUOTE if "emalls" in manual_prices else DataType.ESTIMATE,
                channel_type="search_link",
                fetch_time_utc=now_utc if "emalls" in manual_prices else None
            ),
            IranMarketChannel(
                name="باسلام (Basalam - غرفه‌داران و بنکداران)",
                price_toman=manual_prices.get("basalam"),
                price_label="قیمت ثبت‌شده توسط کاربر" if "basalam" in manual_prices else "لینک جستجوی مستقیم باسلام",
                url=basalam_url,
                is_live=False,
                data_type=DataType.MANUAL_QUOTE if "basalam" in manual_prices else DataType.ESTIMATE,
                channel_type="search_link",
                fetch_time_utc=now_utc if "basalam" in manual_prices else None
            ),
            IranMarketChannel(
                name="دیوار و بازار آزاد (Divar)",
                price_toman=manual_prices.get("divar"),
                price_label="قیمت ثبت‌شده توسط کاربر" if "divar" in manual_prices else "لینک جستجوی مستقیم آگهی‌های دیوار",
                url=divar_url,
                is_live=False,
                data_type=DataType.MANUAL_QUOTE if "divar" in manual_prices else DataType.ESTIMATE,
                channel_type="search_link",
                fetch_time_utc=now_utc if "divar" in manual_prices else None
            )
        ]

        return IranMarketPrice(
            platform="دیجی‌کالا (استعلام زنده) • ترب و ایمالز (لینک مستقیم)",
            title_fa=title_fa,
            lowest_price_toman=lowest,
            average_price_toman=avg,
            highest_price_toman=highest,
            active_sellers_count=sellers_count,
            sales_velocity_score=velocity,
            source_url=torob_url,
            channels=channels,
            sample_products=sample_products,
            status=status,
            data_type=data_type,
            freshness=freshness,
            fetch_time_utc=now_utc
        )
