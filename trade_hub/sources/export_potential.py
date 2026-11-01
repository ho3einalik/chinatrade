"""
ITC Export Potential Map Source Adapter (https://exportpotential.intracen.org/).
Identifies untapped export potential and market diversification opportunities.
"""

from typing import List, Optional
from trade_hub.sources.base import SourceAdapter
from trade_hub.models import NormalizedTradeRecord


class ExportPotentialMapAdapter(SourceAdapter):
    source_id = "export_potential"
    source_name = "ITC Export Potential Map"
    base_url = "https://exportpotential.intracen.org"
    coverage_countries = ["Global (220+ Countries)"]
    coverage_products = "HS6 Products"
    requires_auth = False
    data_nature = "ECONOMETRIC_POTENTIAL_GAP"
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
        exporter = partner_country or "364"  # 364 is Iran ISO numeric
        if clean_hs:
            return f"https://exportpotential.intracen.org/en/markets/gap-chart?fromMarker=i&exporter={exporter}&toMarker=w&product={clean_hs}"
        return f"{self.base_url}/en/markets/gap-chart"

    def parse_import_file(
        self,
        file_content: bytes,
        filename: str,
        hs_code_context: Optional[str] = None
    ) -> List[NormalizedTradeRecord]:
        return []
