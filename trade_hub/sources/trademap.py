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
    coverage_countries = ["جهانی (۲۲۰+ کشور و قلمرو گمرکی)"]
    coverage_products = "کدهای تعرفه ۲، ۴، ۶ رقمی HS و ردیف‌های ملی تعرفه"
    coverage_frequency = "سالانه، فصلی و ماهانه (بروزرسانی رسمی گمرکات دنیا)"
    requires_auth = False  # Public aggregates free; deep company level requires ITC login
    data_nature = "HISTORICAL_ANNUAL_CUSTOMS"
    is_live_api = False    # ITC requires enterprise subscription for automated API; file import + deep links provided
    last_verified_date = "2026-03-01"
    notes = "پایگاه مرجع آمار تجارت بین‌الملل: ارزش دلاری مبادلات، حجم فیزیکی (تن)، قیمت واحد (USD/Ton)، نرخ رشد ۵ ساله، سهم بازار و فهرست واردکنندگان رسمی."

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

    def build_company_directory_url(self, hs_code: str) -> str:
        """Deep-link to verified importers directory in Trade Map."""
        clean_hs = hs_code.replace(".", "").strip()
        return f"https://www.trademap.org/Companies.aspx?nvpm=1|||||{clean_hs}|||2|1|1|1|1||2|1|1"

    def build_bilateral_url(self, hs_code: str, reporter_country: str = "364", partner_country: str = "") -> str:
        """Deep-link to bilateral trade flows between two countries."""
        clean_hs = hs_code.replace(".", "").strip()
        return f"https://www.trademap.org/Bilateral_TS.aspx?nvpm=1|{reporter_country}||{partner_country}||{clean_hs}|||2|1|1|1|1||2|1|1"

    @classmethod
    def parse_csv_export(
        cls,
        text_content: str,
        filename: str = "trademap_export.csv",
        hs_code_context: Optional[str] = None
    ) -> List[NormalizedTradeRecord]:
        """
        Parses authentic ITC Trade Map CSV/TSV table export.
        Extracts:
        - Country/Partner
        - Trade Value USD (handles thousands-multiplier)
        - Quantity & Units
        - Unit Value (USD/Ton or USD/Unit)
        - Growth Rates (5-year CAGR & 1-year annual growth)
        - Market Share %
        """
        results: List[NormalizedTradeRecord] = []
        if not text_content:
            return results

        lines = [line for line in text_content.splitlines() if line.strip()]
        if len(lines) < 2:
            return results

        # Detect delimiter (Tab or Comma or Semicolon)
        first_line = lines[0]
        delimiter = "\t" if "\t" in first_line else (";" if ";" in first_line else ",")
        reader = csv.reader(io.StringIO(text_content), delimiter=delimiter)
        rows = list(reader)

        # Find header row
        header_idx = -1
        for idx, r in enumerate(rows[:15]):
            line_str = " ".join(r).lower()
            if any(k in line_str for k in ("importer", "exporter", "partner", "country", "کشور", "واردکننده")):
                header_idx = idx
                break

        if header_idx == -1:
            header_idx = 0

        headers = [h.strip().lower() for h in rows[header_idx]]
        data_rows = rows[header_idx + 1:]

        country_col = 0
        val_col = -1
        qty_col = -1
        unit_val_col = -1
        growth_col = -1
        growth_1yr_col = -1
        share_col = -1

        for i, h in enumerate(headers):
            if any(k in h for k in ("importer", "exporter", "country", "partner", "کشور", "طرف تجاری")):
                country_col = i
            elif "unit value" in h or "ارزش واحد" in h:
                unit_val_col = i
            elif ("growth" in h or "رشد" in h) and any(y in h for y in ("2020", "2021", "2019", "5", "cagr")):
                growth_col = i
            elif ("growth" in h or "رشد" in h) and any(y in h for y in ("2023-2024", "2024-2025", "1")):
                growth_1yr_col = i
            elif "growth" in h or "trend" in h or "رشد" in h:
                if growth_col == -1:
                    growth_col = i
            elif "share" in h or "سهم" in h:
                share_col = i
            elif "quantity" in h or "مقدار" in h:
                qty_col = i
            elif "value" in h and not any(ex in h for ex in ("unit", "growth", "واحد", "رشد")):
                if any(yr in h for yr in ("2025", "2024", "2023", "2022")):
                    val_col = i
                elif val_col == -1:
                    val_col = i

        for r in data_rows:
            if not r or len(r) <= country_col:
                continue
            country_name = r[country_col].strip()
            if not country_name or any(w in country_name.lower() for w in ("world", "total", "مجموع", "جهان")):
                continue

            def _parse_dec(idx: int) -> Optional[Decimal]:
                if 0 <= idx < len(r):
                    val_str = r[idx].replace(",", "").replace("$", "").replace("%", "").strip()
                    try:
                        return Decimal(val_str)
                    except Exception:
                        return None
                return None

            val_dec = _parse_dec(val_col) or Decimal("0")
            # Trade Map values in tables are frequently expressed in thousands of USD
            trade_val = val_dec * Decimal("1000") if Decimal("0") < val_dec < Decimal("1000000") else val_dec
            growth_val = _parse_dec(growth_col)
            growth_1yr = _parse_dec(growth_1yr_col)
            unit_val = _parse_dec(unit_val_col)
            qty_val = _parse_dec(qty_col)
            share_val = _parse_dec(share_col)

            results.append(NormalizedTradeRecord(
                source_id=cls.source_id,
                source_name=cls.source_name,
                source_url=f"https://www.trademap.org/Country_SelProduct.aspx?nvpm=1|||||{(hs_code_context or '').replace('.', '')}|||2|1|1|1|1||2|1|1",
                country_origin="World",
                country_destination=country_name,
                hs_code=hs_code_context or "HS-GENERIC",
                trade_value_usd=trade_val,
                trade_quantity=qty_val,
                quantity_unit="Tons",
                unit_value_usd=unit_val,
                annual_growth_rate_pct=growth_val or growth_1yr,
                market_share_pct=share_val,
                evidence_type=EvidenceType.OFFICIAL_CUSTOMS,
                confidence_level=ConfidenceLevel.HIGH,
                notes=f"استخراج‌شده از فایل گزارش رسمی Trade Map ({filename})"
            ))

        return results

    def parse_import_file(
        self,
        file_content: bytes,
        filename: str,
        hs_code_context: Optional[str] = None
    ) -> List[NormalizedTradeRecord]:
        """Parses official ITC Trade Map CSV/TSV export from bytes."""
        text = ""
        for encoding in ("utf-8", "utf-8-sig", "utf-16", "latin-1"):
            try:
                text = file_content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if not text:
            return []

        return self.parse_csv_export(
            text_content=text,
            filename=filename,
            hs_code_context=hs_code_context
        )
