"""
Unified Trade Sources Registry.
Manages adapter lifecycle, query distribution, and metadata introspection.
"""

from typing import Dict, List, Optional, Any
from trade_hub.models import NormalizedTradeRecord, EvidenceType, ConfidenceLevel
from decimal import Decimal
from trade_hub.sources.base import SourceAdapter
from trade_hub.sources.trademap import TradeMapAdapter
from trade_hub.sources.comtrade import UNComtradeAdapter
from trade_hub.sources.macmap import MarketAccessMapAdapter
from trade_hub.sources.export_potential import ExportPotentialMapAdapter
from trade_hub.sources.tpo_iran import TPOIranAdapter
from trade_hub.sources.iriqcc import IRIQCCAdapter
from trade_hub.sources.parsgoods import ParsGoodsAdapter


class TradeSourcesRegistry:
    def __init__(self):
        self._adapters: Dict[str, SourceAdapter] = {
            "trademap": TradeMapAdapter(),
            "comtrade": UNComtradeAdapter(),
            "macmap": MarketAccessMapAdapter(),
            "export_potential": ExportPotentialMapAdapter(),
            "tpo_iran": TPOIranAdapter(),
            "ir_iqcc": IRIQCCAdapter(),
            "parsgoods": ParsGoodsAdapter()
        }

    def get_adapter(self, source_id: str) -> Optional[SourceAdapter]:
        return self._adapters.get(source_id)

    def list_all_sources(self) -> List[Dict[str, Any]]:
        return [adapter.get_metadata() for adapter in self._adapters.values()]

    def list_sources(self) -> List[Dict[str, Any]]:
        return self.list_all_sources()

    def search_all(
        self,
        query: str = "",
        hs_code: Optional[str] = None,
        country: Optional[str] = None
    ) -> List[NormalizedTradeRecord]:
        """
        Queries all active source adapters that support parametric search.
        """
        results: List[NormalizedTradeRecord] = []
        # Query Comtrade adapter
        comtrade = self._adapters.get("comtrade")
        if comtrade and hs_code:
            try:
                records = comtrade.query_hs_code(hs_code=hs_code, reporter=country)
                results.extend(records)
            except Exception:
                pass

        # Query ParsGoods for directory leads
        parsgoods = self._adapters.get("parsgoods")
        if parsgoods and query:
            try:
                records = parsgoods.search_exporters(query=query)
                results.extend(records)
            except Exception:
                pass

        return results

    def generate_all_search_links(
        self,
        query: str,
        hs_code: Optional[str] = None,
        country: Optional[str] = None,
        partner_country: Optional[str] = None
    ) -> Dict[str, Dict[str, any]]:
        links = {}
        for sid, adapter in self._adapters.items():
            meta = adapter.get_metadata()
            url = adapter.build_search_url(
                query=query,
                hs_code=hs_code,
                country=country,
                partner_country=partner_country
            )
            links[sid] = {
                "source_id": sid,
                "name": meta["source_name"],
                "url": url,
                "coverage_countries": meta["coverage_countries"],
                "data_nature": meta["data_nature"],
                "requires_auth": meta["requires_auth"],
                "is_live_api": meta["is_live_api"]
            }
        return links
