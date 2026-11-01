"""
ITC Trade Map Source Adapter (https://www.trademap.org/).
Provides parametric deep-search URLs and parses authentic Trade Map CSV/TSV exports.
"""

import io
import csv
import urllib.parse
from decimal import Decimal
from typing import List, Optional
from trade_hub.sources.base import SourceAdapter
from trade_hub.models import NormalizedTradeRecord, EvidenceType, ConfidenceLevel


class TradeMapAdapter(SourceAdapter):
    source_id = "trademap"
    source_name = "ITC Trade Map (International Trade Centre)"
    base_url = "https://www.trademap.org"
    coverage_countries = ["Global (220+ Countries and Territories)"]
    coverage_products = "HS2, HS4, HS6, HS8, National Tariffs"
    requires_auth = False  # Public aggregates free; deep company level requires ITC login
    data_nature = "HISTORICAL_ANNUAL_CUSTOMS"
    is_live_api = False    # ITC requires enterprise subscription for automated API; file import + deep links provided
    last_verified_date = "2026-03-01"

    def build_search_url(
        self,
        query: str = "",
        hs_code: Optional[str] = None,
        country: Optional[str] = None,
        partner_country: Optional[str] = None
    ) -> str:
        clean_hs = (hs_code or "").replace(".", "").strip()
        if clean_hs:
            # Direct product import/export analysis page
            return f"https://www.trademap.org/Country_SelProduct.aspx?nvpm=1|||||{clean_hs}|||2|1|1|1|1||2|1|1"
        elif query:
            encoded_q = urllib.parse.quote(query)
            return f"https://www.trademap.org/Product_SelProduct_TS.aspx?nvpm=1|||||||||2|1|1|1|1||2|1|1&keywords={encoded_q}"
        return self.base_url

    def parse_import_file(
        self,
        file_content: bytes,
        filename: str,
        hs_code_context: Optional[str] = None
    ) -> List[NormalizedTradeRecord]:
        """
        Parses official ITC Trade Map CSV/TSV export.
        Handles headers such as:
        'Importers', 'Value imported in 2023', 'Value imported in 2024',
        'Quantity imported in 2024', 'Unit value (USD/unit)', 'Share in world imports (%)'
        """
        results: List[NormalizedTradeRecord] = []
        try:
            # Decode UTF-8 or UTF-16 (Trade Map sometimes exports UTF-16 tab-delimited)
            text = ""
            for encoding in ("utf-8", "utf-16", "latin-1"):
                try:
                    text = file_content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if not text:
                return results

            # Detect delimiter (Tab or Comma)
            delimiter = "\t" if "\t" in text.splitlines()[0] else ","
            reader = csv.reader(io.StringIO(text), delimiter=delimiter)
            rows = list(reader)

            if len(rows) < 2:
                return results

            # Find header row
            header_idx = -1
            for idx, r in enumerate(rows[:10]):
                line_str = " ".join(r).lower()
                if "importer" in line_str or "exporter" in line_str or "partner" in line_str or "country" in line_str:
                    header_idx = idx
                    break

            if header_idx == -1:
                header_idx = 0

            headers = [h.strip().lower() for h in rows[header_idx]]
            data_rows = rows[header_idx + 1:]

            # Identify key columns
            country_col = 0
            val_col = -1
            qty_col = -1
            unit_val_col = -1
            growth_col = -1
            share_col = -1

            for i, h in enumerate(headers):
                if any(k in h for k in ("importer", "exporter", "country", "partner")):
                    country_col = i
                elif "value" in h and any(yr in h for yr in ("2024", "2023", "2025")):
                    val_col = i
                elif val_col == -1 and "value" in h:
                    val_col = i
                elif "quantity" in h:
                    qty_col = i
                elif "unit value" in h:
                    unit_val_col = i
                elif "growth" in h or "trend" in h:
                    growth_col = i
                elif "share" in h:
                    share_col = i

            for r in data_rows:
                if not r or len(r) <= country_col:
                    continue
                country_name = r[country_col].strip()
                if not country_name or "world" in country_name.lower() or "total" in country_name.lower():
                    continue

                def _parse_dec(idx: int) -> Optional[Decimal]:
                    if idx >= 0 and idx < len(r):
                        val_str = r[idx].replace(",", "").replace("$", "").replace("%", "").strip()
                        try:
                            return Decimal(val_str)
                        except Exception:
                            return None
                    return None

                val_dec = _parse_dec(val_col) or Decimal("0")
                # Trade Map values in tables are frequently in thousands of USD
                trade_val = val_dec * Decimal("1000") if val_dec > 0 and val_dec < Decimal("1000000") else val_dec

                results.append(NormalizedTradeRecord(
                    source_id=self.source_id,
                    source_name=self.source_name,
                    source_url=self.build_search_url(hs_code=hs_code_context),
                    country_origin="World",
                    country_destination=country_name,
                    hs_code=hs_code_context or "HS-GENERIC",
                    trade_value_usd=trade_val,
                    trade_quantity=_parse_dec(qty_col),
                    quantity_unit="Tons",
                    unit_value_usd=_parse_dec(unit_val_col),
                    annual_growth_rate_pct=_parse_dec(growth_col),
                    market_share_pct=_parse_dec(share_col),
                    evidence_type=EvidenceType.OFFICIAL_CUSTOMS,
                    confidence_level=ConfidenceLevel.HIGH,
                    notes=f"Parsed from Trade Map export file '{filename}'"
                ))

        except Exception as e:
            # Gracefully fail on corrupt format
            pass

        return results
