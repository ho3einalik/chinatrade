"""
Iran Trade Promotion Organization Source Adapter (http://tpo.ir/).
Provides trade statistics, export incentives, international treaties, and commercial events.
"""

import urllib.parse
from typing import List, Optional
from trade_hub.sources.base import SourceAdapter
from trade_hub.models import NormalizedTradeRecord


class TPOIranAdapter(SourceAdapter):
    source_id = "tpo_iran"
    source_name = "سازمان توسعه تجارت ایران (TPO)"
    base_url = "http://tpo.ir"
    coverage_countries = ["Iran Trade Partners (EAEU, Iraq, UAE, Turkey, China, India, Oman, Pakistan)"]
    coverage_products = "Iran Export Commodities & Preferential Tariffs"
    requires_auth = False
    data_nature = "OFFICIAL_CHAMBER_REGULATORY"
    is_live_api = False
    last_verified_date = "2026-03-01"

    def build_search_url(
        self,
        query: str = "",
        hs_code: Optional[str] = None,
        country: Optional[str] = None,
        partner_country: Optional[str] = None
    ) -> str:
        if query:
            encoded = urllib.parse.quote(query)
            return f"http://tpo.ir/search?q={encoded}"
        return self.base_url

    def get_preferential_agreements(self) -> List[dict]:
        """Official preferential and free trade trade treaties signed by Iran."""
        return [
            {
                "agreement_name": "موافقت‌نامه تجارت ترجیحی و آزاد با اتحادیه اقتصادی اوراسیا (EAEU)",
                "countries": ["روسیه", "قزاقستان", "بلاروس", "ارمنستان", "قرقیزستان"],
                "status": "لازم‌الاجرا",
                "tariff_reduction": "تخفیف تعرفه‌ای ۸۰٪ تا ۱۰۰٪ بر اقلام کشاورزی و صنعتی مصوب",
                "certificate_of_origin": "گواهی مبدأ فرم CT-3"
            },
            {
                "agreement_name": "موافقت‌نامه تجارت ترجیحی ایران و ترکیه",
                "countries": ["ترکیه"],
                "status": "فعال",
                "tariff_reduction": "تخفیف‌های تعرفه‌ای دوجانبه برای ۱۲۵ قلم کالای صنعتی و کشاورزی",
                "certificate_of_origin": "گواهی مبدأ ویژه موافقت‌نامه ایران-ترکیه"
            },
            {
                "agreement_name": "موافقت‌نامه تجارت آزاد ایران و سوریه",
                "countries": ["سوریه"],
                "status": "فعال",
                "tariff_reduction": "عوارض گمرکی حداکثر ۴٪ برای تمامی کالاهای غیرممنوعه",
                "certificate_of_origin": "گواهی مبدأ مصوب اتاق بازرگانی"
            },
            {
                "agreement_name": "موافقت‌نامه تجارت ترجیحی ایران و پاکستان",
                "countries": ["پاکستان"],
                "status": "فعال",
                "tariff_reduction": "تخفیف‌های ۱۰ تا ۳۰ درصدی حقوق گمرکی در مبادلات مرزی و بنادر",
                "certificate_of_origin": "گواهی مبدأ فرم A / عادی"
            }
        ]

    def parse_import_file(
        self,
        file_content: bytes,
        filename: str,
        hs_code_context: Optional[str] = None
    ) -> List[NormalizedTradeRecord]:
        return []
