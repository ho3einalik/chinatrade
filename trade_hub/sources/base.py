"""
Base Source Adapter contract for Trade Intelligence Hub.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from trade_hub.models import NormalizedTradeRecord


class SourceAdapter(ABC):
    """
    Abstract contract for all international trade and market data sources.
    Guarantees strict attribution, metadata transparency, and safe file parsing.
    """
    source_id: str
    source_name: str
    base_url: str
    coverage_countries: List[str]
    coverage_products: str
    requires_auth: bool
    data_nature: str
    is_live_api: bool
    last_verified_date: str = "2026-03-01"

    @abstractmethod
    def build_search_url(
        self,
        query: str = "",
        hs_code: Optional[str] = None,
        country: Optional[str] = None,
        partner_country: Optional[str] = None
    ) -> str:
        """Generates authentic, verified deep-link directly to source query page."""
        pass

    @abstractmethod
    def parse_import_file(
        self,
        file_content: bytes,
        filename: str,
        hs_code_context: Optional[str] = None
    ) -> List[NormalizedTradeRecord]:
        """Parses legal user-uploaded CSV, TSV, or Excel export files into NormalizedTradeRecord."""
        pass

    coverage_frequency: str = "سالانه و فصلی"
    notes: str = ""

    def get_metadata(self) -> Dict[str, Any]:
        """Returns source specifications for display in UI and audit reports."""
        geo = ", ".join(self.coverage_countries) if isinstance(self.coverage_countries, list) else str(self.coverage_countries)
        status_label = "ACTIVE_DIRECT" if self.is_live_api else "PORTAL_SEARCH"
        return {
            "source_id": self.source_id,
            "name": self.source_name,
            "source_name": self.source_name,
            "base_url": self.base_url,
            "operational_status": status_label,
            "coverage_geography": geo,
            "coverage_frequency": getattr(self, "coverage_frequency", "آمار گمرکی سالانه و فصلی"),
            "notes": getattr(self, "notes", self.data_nature),
            "coverage_countries": self.coverage_countries,
            "coverage_products": self.coverage_products,
            "requires_auth": self.requires_auth,
            "data_nature": self.data_nature,
            "is_live_api": self.is_live_api,
            "last_verified_date": self.last_verified_date
        }
