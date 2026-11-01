"""
CSV & Excel Batch Importer for My Trade Network contacts.
Sanitizes inputs against CSV injection and validates schemas.
"""

import io
import csv
from decimal import Decimal
from typing import List, Dict, Any, Optional, Union
from trade_hub.db import TradeHubDatabase
from trade_hub.models import PrivateContact, TradeRole, GlobalIncoterms, VerificationStatus
from trade_hub.network.repository import TradeNetworkRepository


def sanitize_cell(value: str) -> str:
    """Protects against CSV Formula Injection (=, +, -, @, tab, cr)."""
    val = (value or "").strip()
    if val and val[0] in ("=", "+", "-", "@", "\t", "\r"):
        val = "'" + val
    return val


class NetworkBatchImporter:
    def __init__(self, repo: TradeNetworkRepository):
        self.repo = repo

    def import_csv_content(self, csv_bytes: bytes, filename: str, tenant_id: str = "default_importer") -> Dict[str, Any]:
        """
        Parses CSV with standard headers:
        name, country, role (BUYER/SUPPLIER/BOTH), contact_person, email, phone, website,
        products (comma-separated), hs_codes, moq, unit_price_usd, incoterms, notes
        """
        text = ""
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                text = csv_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if not text:
            return {"status": "error", "message": "قالب فایل نامعتبر یا غیرقابل رمزگشایی است.", "imported": 0, "duplicates": 0}

        reader = csv.DictReader(io.StringIO(text))
        imported_count = 0
        duplicates_count = 0

        for row in reader:
            clean_row = {k.strip().lower() if k else "": sanitize_cell(v) for k, v in row.items()}
            name = clean_row.get("name", clean_row.get("company_name", clean_row.get("شرکت", "")))
            country = clean_row.get("country", clean_row.get("کشور", "Unknown"))
            if not name:
                continue

            role_str = clean_row.get("role", "BOTH").upper()
            role = TradeRole(role_str) if role_str in TradeRole.__members__ else TradeRole.BOTH

            prods_raw = clean_row.get("products", clean_row.get("محصولات", ""))
            prods = [p.strip() for p in prods_raw.split(";") if p.strip()] or [p.strip() for p in prods_raw.split(",") if p.strip()]
            
            hs_raw = clean_row.get("hs_codes", clean_row.get("hs_code", ""))
            hs_list = [h.strip() for h in hs_raw.split(",") if h.strip()]

            price_raw = clean_row.get("unit_price_usd", clean_row.get("price", ""))
            price_dec = None
            if price_raw:
                try:
                    price_dec = Decimal(price_raw.replace("$", "").replace(",", "").strip())
                except Exception:
                    price_dec = None

            moq_raw = clean_row.get("moq", "")
            moq_val = int(moq_raw) if moq_raw.isdigit() else None

            incoterm_raw = clean_row.get("incoterms", "FOB").upper()
            incoterm = GlobalIncoterms(incoterm_raw) if incoterm_raw in GlobalIncoterms.__members__ else GlobalIncoterms.FOB

            contact = PrivateContact(
                tenant_id=tenant_id,
                name=name,
                country=country,
                city=clean_row.get("city", ""),
                role=role,
                contact_person=clean_row.get("contact_person", ""),
                email=clean_row.get("email", ""),
                phone=clean_row.get("phone", ""),
                website=clean_row.get("website", ""),
                products=prods,
                hs_codes=hs_list,
                moq=moq_val,
                unit_price_usd=price_dec,
                incoterms=incoterm,
                source_reference=f"CSV Import: {filename}",
                private_notes=clean_row.get("notes", "")
            )

            _, is_new = self.repo.add_contact(contact)
            if is_new:
                imported_count += 1
            else:
                duplicates_count += 1

        return {
            "status": "success",
            "imported": imported_count,
            "duplicates": duplicates_count,
            "filename": filename
        }

    @classmethod
    def import_csv(
        cls,
        csv_text_or_bytes: Union[str, bytes],
        tenant_id: str = "default_importer",
        db: Optional[TradeHubDatabase] = None
    ) -> Dict[str, Any]:
        """Convenience method for string or byte batch CSV import."""
        raw_bytes = csv_text_or_bytes.encode("utf-8") if isinstance(csv_text_or_bytes, str) else csv_text_or_bytes
        repo = TradeNetworkRepository(db or TradeHubDatabase())
        importer = cls(repo)
        res = importer.import_csv_content(raw_bytes, "batch_import.csv", tenant_id=tenant_id)
        return {
            "status": "success",
            "imported_count": res.get("imported", 0),
            "duplicate_count": res.get("duplicates", 0),
            "message": f"{res.get('imported', 0)} مخاطب با موفقیت وارد شدند."
        }
