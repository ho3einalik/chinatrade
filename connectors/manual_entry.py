"""
Manual Quotation & CSV/Excel Entry Connector.
Allows importing custom Chinese supplier quotations from proforma invoices,
direct WeChat/WhatsApp factory negotiations, and bulk tabular uploads.
"""

import csv
import io
import json
from typing import List, Dict, Any, Union, Optional
from pydantic import ValidationError
from core.models import ChineseSupplier, PriceTier, DataType, Incoterms, VerificationStatus, DataFreshness

class ManualQuotationParser:
    @staticmethod
    def parse_dict_to_supplier(data: Dict[str, Any]) -> ChineseSupplier:
        """
        Validates and converts a raw dictionary to a standard ChineseSupplier model.
        """
        # Ensure price tiers are formatted correctly if provided
        raw_tiers = data.get("price_tiers", [])
        tiers: List[PriceTier] = []
        if isinstance(raw_tiers, list):
            for t in raw_tiers:
                if isinstance(t, dict) and "min_quantity" in t and "unit_price_cny" in t:
                    tiers.append(PriceTier(
                        min_quantity=int(t["min_quantity"]),
                        unit_price_cny=float(t["unit_price_cny"]),
                        unit_price_usd=float(t.get("unit_price_usd")) if t.get("unit_price_usd") is not None else None
                    ))

        incoterms_str = str(data.get("incoterms", "EXW")).upper()
        try:
            incoterms_val = Incoterms(incoterms_str)
        except ValueError:
            incoterms_val = Incoterms.EXW

        data_type_val = DataType(data.get("data_type", "manual_quote")) if data.get("data_type") in DataType._value2member_map_ else DataType.MANUAL_QUOTE

        return ChineseSupplier(
            name=str(data.get("name") or data.get("supplier_name", "تأمین‌کننده دستی (ورودی کاربر)")).strip(),
            platform=str(data.get("platform", "Manual Proforma Invoice / WeChat")).strip(),
            product_title=str(data.get("product_title") or data.get("title", "")).strip(),
            product_specs=data.get("product_specs") if isinstance(data.get("product_specs"), dict) else {},
            unit_price_cny=float(data.get("unit_price_cny", 0.0)),
            unit_price_usd=float(data.get("unit_price_usd")) if data.get("unit_price_usd") is not None else None,
            price_tiers=tiers,
            moq=int(data.get("moq", 1)),
            supplier_tier=str(data.get("supplier_tier", "Manual Verified")),
            years_active=int(data.get("years_active", 1)),
            location=str(data.get("location", "China")),
            certifications=data.get("certifications", []) if isinstance(data.get("certifications"), list) else [],
            lead_time_days=int(data.get("lead_time_days", 10)),
            weight_kg=float(data.get("weight_kg", 0.2)),
            volume_cbm=float(data.get("volume_cbm", 0.001)),
            source_url=str(data.get("source_url", "")).strip(),
            data_type=data_type_val,
            incoterms=incoterms_val,
            verification_status=VerificationStatus.VERIFIED_WITH_DOCS,
            freshness=DataFreshness.FRESH,
            confidence_level="REAL_USER_PROFORMA",
            is_demo=False
        )

    @classmethod
    def parse_csv_content(cls, csv_text: str) -> List[ChineseSupplier]:
        """
        Parses CSV data containing supplier quotation records.
        Expected headers (case-insensitive):
        name, platform, product_title, unit_price_cny, moq, weight_kg, volume_cbm, lead_time_days, incoterms
        """
        suppliers: List[ChineseSupplier] = []
        f = io.StringIO(csv_text.strip())
        reader = csv.DictReader(f)
        
        for row in reader:
            normalized_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            if not normalized_row.get("product_title") and not normalized_row.get("unit_price_cny"):
                continue

            try:
                supp = cls.parse_dict_to_supplier({
                    "name": normalized_row.get("name") or normalized_row.get("supplier_name", "کارخانه چینی"),
                    "platform": normalized_row.get("platform", "Manual CSV Import"),
                    "product_title": normalized_row.get("product_title", ""),
                    "unit_price_cny": float(normalized_row.get("unit_price_cny", 0.0)),
                    "moq": int(normalized_row.get("moq", 1)),
                    "weight_kg": float(normalized_row.get("weight_kg", 0.2)),
                    "volume_cbm": float(normalized_row.get("volume_cbm", 0.001)),
                    "lead_time_days": int(normalized_row.get("lead_time_days", 10)),
                    "location": normalized_row.get("location", "Guangdong, China"),
                    "source_url": normalized_row.get("source_url", ""),
                    "incoterms": normalized_row.get("incoterms", "EXW"),
                    "data_type": "csv_import"
                })
                suppliers.append(supp)
            except (ValueError, ValidationError) as e:
                continue

        return suppliers
