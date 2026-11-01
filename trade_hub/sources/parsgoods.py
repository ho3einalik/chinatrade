"""
ParsGoods Source Adapter (https://parsgoods.com/fa).
Exporters directory, product showcases, and Iranian export B2B catalog.
"""

import urllib.parse
from typing import List, Optional
from trade_hub.sources.base import SourceAdapter
from trade_hub.models import NormalizedTradeRecord


class ParsGoodsAdapter(SourceAdapter):
    source_id = "parsgoods"
    source_name = "پارس‌گودز (ParsGoods - صادرات کالاهای ایرانی)"
    base_url = "https://parsgoods.com/fa"
    coverage_countries = ["ایران", "کشورهای هدف صادراتی (خاورمیانه، CIS، اروپا، آفریقا)"]
    coverage_products = "کالاهای تولیدی ایران (پتروشیمی، کشاورزی، صنایع دستی، مواد ساختمانی)"
    coverage_frequency = "پایگاه داده زنده شرکت‌ها و شوروم آنلاین"
    notes = "بانک اطلاعات تامین‌کنندگان و صادرکنندگان معتبر ایرانی، کاتالوگ‌های چندزبانه صادراتی و ایجاد کانال معرفی محصولات به مشتریان خارجی."
    requires_auth = False
    data_nature = "B2B_EXPORTER_DIRECTORY"
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
            return f"https://parsgoods.com/fa/search?q={encoded}"
        return self.base_url

    def parse_import_file(
        self,
        file_content: bytes,
        filename: str,
        hs_code_context: Optional[str] = None
    ) -> List[NormalizedTradeRecord]:
        return []
