"""
UN Comtrade Source Adapter (https://comtradeplus.un.org/).
Interfaces UN Statistics Division international commodity trade data.
"""

import io
import csv
import json
import urllib.parse
from decimal import Decimal
from typing import List, Optional
from trade_hub.sources.base import SourceAdapter
from trade_hub.models import NormalizedTradeRecord, EvidenceType, ConfidenceLevel


class UNComtradeAdapter(SourceAdapter):
    source_id = "comtrade"
    source_name = "UN Comtrade (United Nations Statistics Division)"
    base_url = "https://comtradeplus.un.org"
    coverage_countries = ["جهانی (تمامی ۱۹۳ کشور عضو سازمان ملل)"]
    coverage_products = "کالاهای تجاری HS دو تا شش رقمی"
    coverage_frequency = "سالانه و ماهانه (کوئری زنده API رسمی سازمان ملل)"
    requires_auth = False  # Public portal query is open; API v1 high-volume requires Primary Key
    data_nature = "HISTORICAL_OFFICIAL_CUSTOMS"
    is_live_api = True
    last_verified_date = "2026-03-01"
    notes = "آمار رسمی تجارت کالایی ملل متحد (UNSD): جریان‌های دوجانبه مبادلات کشورها، ارزش دلاری، وزن خالص و استعلام زنده API."

    def build_search_url(
        self,
        query: str = "",
        hs_code: Optional[str] = None,
        country: Optional[str] = None,
        partner_country: Optional[str] = None
    ) -> str:
        clean_hs = (hs_code or "").replace(".", "").strip()
        params = ["Frequency=A", "Flows=M"]  # Annual, Imports
        if clean_hs:
            params.append(f"CommodityCodes={clean_hs}")
        return f"https://comtradeplus.un.org/TradeFlow?{'&'.join(params)}"

    def parse_api_response(self, json_data: dict, hs_code_context: str = "") -> List[NormalizedTradeRecord]:
        """Maps standard UN Comtrade v1 data response array to NormalizedTradeRecord list."""
        records: List[NormalizedTradeRecord] = []
        data_rows = json_data.get("data", []) if isinstance(json_data, dict) else []
        for item in data_rows:
            reporter = item.get("reporterDesc", item.get("reporterCode", "Unknown"))
            partner = item.get("partnerDesc", item.get("partnerCode", "World"))
            trade_val = Decimal(str(item.get("primaryValue", 0)))
            qty = Decimal(str(item.get("qty", 0))) if item.get("qty") else None
            period = str(item.get("period", "2024"))
            cmd_code = str(item.get("cmdCode", hs_code_context))

            records.append(NormalizedTradeRecord(
                source_id=self.source_id,
                source_name=self.source_name,
                source_url=self.build_search_url(hs_code=cmd_code),
                country_origin=partner,
                country_destination=reporter,
                hs_code=cmd_code,
                product_title_en=item.get("cmdDesc", ""),
                trade_value_usd=trade_val,
                trade_quantity=qty,
                quantity_unit=item.get("qtyUnitAbbr", "KG"),
                data_period=period,
                evidence_type=EvidenceType.OFFICIAL_CUSTOMS,
                confidence_level=ConfidenceLevel.HIGH,
                is_mirror_data=bool(item.get("isMirror", False)),
                notes="Verified UN Comtrade statistical dataset"
            ))
        return records

    def parse_import_file(
        self,
        file_content: bytes,
        filename: str,
        hs_code_context: Optional[str] = None
    ) -> List[NormalizedTradeRecord]:
        try:
            # First attempt JSON parse
            try:
                data = json.loads(file_content.decode("utf-8"))
                return self.parse_api_response(data, hs_code_context or "")
            except Exception:
                pass

            # Otherwise attempt standard CSV parse
            text = file_content.decode("utf-8", errors="ignore")
            reader = csv.DictReader(io.StringIO(text))
            records: List[NormalizedTradeRecord] = []
            for row in reader:
                reporter = row.get("Reporter", row.get("reporterDesc", "Unknown"))
                partner = row.get("Partner", row.get("partnerDesc", "World"))
                val_raw = row.get("Trade Value (US$)", row.get("primaryValue", "0")).replace(",", "")
                val_dec = Decimal(val_raw) if val_raw else Decimal("0")

                records.append(NormalizedTradeRecord(
                    source_id=self.source_id,
                    source_name=self.source_name,
                    source_url=self.build_search_url(hs_code=hs_code_context),
                    country_origin=partner,
                    country_destination=reporter,
                    hs_code=row.get("Commodity Code", hs_code_context or "HS-GENERIC"),
                    trade_value_usd=val_dec,
                    data_period=row.get("Year", "2024"),
                    evidence_type=EvidenceType.OFFICIAL_CUSTOMS,
                    confidence_level=ConfidenceLevel.HIGH,
                    notes=f"Parsed from UN Comtrade CSV file '{filename}'"
                ))
            return records
        except Exception:
            return []
