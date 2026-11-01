"""
Iran-Iraq Joint Chamber of Commerce Source Adapter (http://ir-iqcc.com/).
Provides operational trade information, border customs terminals, and Iraqi market access guidelines.
"""

from typing import List, Optional
from trade_hub.sources.base import SourceAdapter
from trade_hub.models import NormalizedTradeRecord


class IRIQCCAdapter(SourceAdapter):
    source_id = "ir_iqcc"
    source_name = "اتاق مشترک بازرگانی ایران و عراق (IR-IQCC)"
    base_url = "http://ir-iqcc.com"
    coverage_countries = ["ایران", "عراق (شامل اقلیم کردستان و بخش مرکزی/جنوبی)"]
    coverage_products = "صادرات مصالح ساختمانی، پتروشیمی، غذایی، بهداشتی و تجهیزات الکتریکی"
    coverage_frequency = "روزانه و هفتگی (پایش پایانه‌های مرزی)"
    notes = "پایش عملیاتی پایانه‌های مرزی فعال (مهران، شلمچه، پرویزخان، باشماق)، استانداردهای کالایی، الزامات برچسب‌گذاری عربی و عوارض ورود به عراق."
    requires_auth = False
    data_nature = "BORDER_LOGISTICS_REGULATORY"
    is_live_api = False
    last_verified_date = "2026-03-01"

    def build_search_url(
        self,
        query: str = "",
        hs_code: Optional[str] = None,
        country: Optional[str] = None,
        partner_country: Optional[str] = None
    ) -> str:
        return self.base_url

    def get_border_terminals(self) -> List[dict]:
        """Key active trade borders between Iran and Iraq."""
        return [
            {
                "terminal_name": "پایانه مرزی مهران (Mehran / Zurbatiyah)",
                "province_iran": "ایلام",
                "destination_iraq": "واسط / بغداد و مرکز عراق",
                "specialization": "ترانزیت تجاری سنگین، کالاهای اساسی و مصالح ساختمانی",
                "status": "۲۴ ساعته فعال"
            },
            {
                "terminal_name": "پایانه مرزی شلمچه (Shalamcheh)",
                "province_iran": "خوزستان",
                "destination_iraq": "بصره و جنوب عراق",
                "specialization": "آهن‌آلات، کاشی و سرامیک، تره‌بار و لوله‌های صنعتی",
                "status": "فعال"
            },
            {
                "terminal_name": "پایانه مرزی پرویزخان (Parviz Khan)",
                "province_iran": "کرمانشاه",
                "destination_iraq": "سلیمانیه و اقلیم کردستان",
                "specialization": "صادرات صنعتی، فرآورده‌های نفتی و پلاستیک",
                "status": "فعال با ظرفیت بالای ترانزیت"
            },
            {
                "terminal_name": "پایانه مرزی خسروی (Khosravi / Al-Munthiriya)",
                "province_iran": "کرمانشاه",
                "destination_iraq": "دیالی و بغداد",
                "specialization": "کالاهای تندمصرف (FMCG)، لبنیات و مواد غذایی",
                "status": "فعال"
            },
            {
                "terminal_name": "پایانه مرزی تمرچین (Tamarchin / Haji Omaran)",
                "province_iran": "آذربایجان غربی",
                "destination_iraq": "اربیل و شمال عراق",
                "specialization": "محصولات کشاورزی، مصالح و ماشین‌آلات صنعتی",
                "status": "فعال"
            }
        ]

    def parse_import_file(
        self,
        file_content: bytes,
        filename: str,
        hs_code_context: Optional[str] = None
    ) -> List[NormalizedTradeRecord]:
        return []
