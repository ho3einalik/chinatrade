"""
ITC Market Access Map Source Adapter (https://www.macmap.org/).
Provides tariff intelligence, trade agreements, and non-tariff measures.
"""

from typing import List, Optional
from trade_hub.sources.base import SourceAdapter
from trade_hub.models import NormalizedTradeRecord


class MarketAccessMapAdapter(SourceAdapter):
    source_id = "macmap"
    source_name = "ITC Market Access Map (Tariffs & Trade Agreements)"
    base_url = "https://www.macmap.org"
    coverage_countries = ["Global (200+ Countries)"]
    coverage_products = "National Tariff Lines (HS6 to HS12)"
    requires_auth = False
    data_nature = "REGULATORY_TARIFFS"
    is_live_api = False
    last_verified_date = "2026-03-01"

    def build_search_url(
        self,
        query: str = "",
        hs_code: Optional[str] = None,
        country: Optional[str] = None,
        partner_country: Optional[str] = None
    ) -> str:
        clean_hs = (hs_code or "").replace(".", "").strip()
        dest = country or "IRQ"
        origin = partner_country or "IRN"
        if clean_hs:
            return f"https://www.macmap.org/en/customs-duties/results?reporter={dest}&partner={origin}&product={clean_hs}"
        return f"{self.base_url}/en/customs-duties/results"

    def parse_import_file(
        self,
        file_content: bytes,
        filename: str,
        hs_code_context: Optional[str] = None
    ) -> List[NormalizedTradeRecord]:
        return []
