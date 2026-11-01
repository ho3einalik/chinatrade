"""
Isolated SQLite Database Manager for Trade Intelligence Hub.
Uses trade_hub.db with complete physical and logical isolation from itrade.db.
"""

import sqlite3
import json
import os
from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from trade_hub.models import (
    PrivateContact, TradeRole, GlobalIncoterms, VerificationStatus,
    RFQRecord, RFQType, RFQStatus,
    DealRecord, DealStage,
    NormalizedTradeRecord, EvidenceType, ConfidenceLevel
)

DEFAULT_TRADE_DB_PATH = os.getenv("TRADE_HUB_DB_PATH", "trade_hub.db")


class TradeHubDatabase:
    """
    Dedicated database for Trade Intelligence Hub.
    Ensures zero collision or unwanted data leak with China Import module.
    """
    def __init__(self, db_path: str = DEFAULT_TRADE_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Private Trade Network Contacts
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS th_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT DEFAULT 'default_importer',
                name TEXT NOT NULL,
                country TEXT NOT NULL,
                city TEXT DEFAULT '',
                role TEXT DEFAULT 'BOTH',
                contact_person TEXT DEFAULT '',
                email TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                website TEXT DEFAULT '',
                address TEXT DEFAULT '',
                products_json TEXT DEFAULT '[]',
                hs_codes_json TEXT DEFAULT '[]',
                capacity_monthly TEXT DEFAULT '',
                moq INTEGER,
                unit_price_usd REAL,
                price_validity_date TEXT,
                payment_terms TEXT DEFAULT 'T/T',
                incoterms TEXT DEFAULT 'FOB',
                lead_time_days INTEGER,
                certifications_json TEXT DEFAULT '[]',
                source_reference TEXT DEFAULT 'Manual Entry',
                verification_status TEXT DEFAULT 'PRELIMINARY_MATCH',
                private_notes TEXT DEFAULT '',
                tags_json TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 2. RFQ & Trade Opportunities
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS th_rfqs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT DEFAULT 'default_importer',
                rfq_type TEXT DEFAULT 'RFQ',
                status TEXT DEFAULT 'NEW',
                title TEXT NOT NULL,
                product_name TEXT NOT NULL,
                hs_code TEXT,
                origin_country TEXT DEFAULT 'Iran',
                target_country TEXT DEFAULT 'Iraq',
                target_quantity REAL DEFAULT 1000,
                unit TEXT DEFAULT 'Tons',
                target_price_usd REAL,
                incoterms TEXT DEFAULT 'CIF',
                payment_terms TEXT DEFAULT 'T/T',
                deadline_date TEXT,
                contact_id INTEGER,
                contact_name TEXT,
                evidence_source TEXT DEFAULT 'Private RFQ',
                specs_summary TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 3. CRM Deals & Negotiations Pipeline
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS th_deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT DEFAULT 'default_importer',
                deal_title TEXT NOT NULL,
                stage TEXT DEFAULT 'DISCOVERY',
                rfq_id INTEGER,
                buyer_name TEXT NOT NULL,
                supplier_name TEXT NOT NULL,
                product_name TEXT NOT NULL,
                hs_code TEXT,
                quantity REAL NOT NULL,
                unit TEXT DEFAULT 'Tons',
                contract_value_usd REAL NOT NULL,
                estimated_cost_usd REAL NOT NULL,
                estimated_profit_usd REAL NOT NULL,
                profit_margin_pct REAL NOT NULL,
                origin_country TEXT NOT NULL,
                destination_country TEXT NOT NULL,
                incoterms TEXT DEFAULT 'FOB',
                assigned_to TEXT DEFAULT 'Trade Manager',
                next_action TEXT DEFAULT 'Follow-up',
                next_followup_date TEXT,
                win_loss_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 4. Normalized Trade Statistics Records (e.g. from Trade Map, Comtrade)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS th_trade_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_url TEXT DEFAULT '',
                external_record_id TEXT,
                retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                published_at TEXT,
                data_period TEXT DEFAULT '2024',
                country_origin TEXT NOT NULL,
                country_destination TEXT NOT NULL,
                hs_code TEXT NOT NULL,
                product_title_en TEXT DEFAULT '',
                product_title_fa TEXT DEFAULT '',
                trade_value_usd REAL DEFAULT 0,
                trade_quantity REAL,
                quantity_unit TEXT DEFAULT 'Tons',
                unit_value_usd REAL,
                annual_growth_rate_pct REAL,
                market_share_pct REAL,
                evidence_type TEXT DEFAULT 'OFFICIAL_CUSTOMS',
                confidence_level TEXT DEFAULT 'HIGH',
                is_mirror_data BOOLEAN DEFAULT 0,
                notes TEXT DEFAULT ''
            )
            """)

            # 5. Saved Market Dossiers & Reports
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS th_market_dossiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dossier_type TEXT NOT NULL, -- 'SELLER', 'BUYER', 'DISCOVERY'
                query_title TEXT NOT NULL,
                hs_code TEXT,
                country TEXT,
                dossier_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 6. Audit Logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS th_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT DEFAULT 'default_importer',
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                details TEXT,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            conn.commit()

    # ----------------------------------------------------------------------
    # Contact Operations
    # ----------------------------------------------------------------------

    def add_contact(self, contact: PrivateContact) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO th_contacts (
                    tenant_id, name, country, city, role, contact_person, email, phone,
                    website, address, products_json, hs_codes_json, capacity_monthly,
                    moq, unit_price_usd, price_validity_date, payment_terms, incoterms,
                    lead_time_days, certifications_json, source_reference,
                    verification_status, private_notes, tags_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contact.tenant_id, contact.name.strip(), contact.country.strip(), contact.city.strip(),
                contact.role.value, contact.contact_person.strip(), contact.email.strip(),
                contact.phone.strip(), contact.website.strip(), contact.address.strip(),
                json.dumps(contact.products, ensure_ascii=False),
                json.dumps(contact.hs_codes, ensure_ascii=False),
                contact.capacity_monthly.strip(), contact.moq,
                float(contact.unit_price_usd) if contact.unit_price_usd is not None else None,
                contact.price_validity_date, contact.payment_terms, contact.incoterms.value,
                contact.lead_time_days,
                json.dumps(contact.certifications, ensure_ascii=False),
                contact.source_reference, contact.verification_status.value,
                contact.private_notes, json.dumps(contact.tags, ensure_ascii=False),
                now, now
            ))
            conn.commit()
            return cursor.lastrowid

    def save_contact(self, contact: PrivateContact) -> int:
        return self.add_contact(contact)

    def list_contacts(
        self,
        role: Optional[TradeRole] = None,
        country: Optional[str] = None,
        search: Optional[str] = None,
        tenant_id: str = "default_importer"
    ) -> List[PrivateContact]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM th_contacts WHERE tenant_id = ?"
            params: List[Any] = [tenant_id]

            if role:
                query += " AND (role = ? OR role = 'BOTH')"
                params.append(role.value)

            if country:
                query += " AND country LIKE ?"
                params.append(f"%{country.strip()}%")

            if search:
                s = f"%{search.strip()}%"
                query += " AND (name LIKE ? OR products_json LIKE ? OR hs_codes_json LIKE ?)"
                params.extend([s, s, s])

            query += " ORDER BY id DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_contact(r) for r in rows]

    def get_contact_by_id(self, contact_id: int) -> Optional[PrivateContact]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM th_contacts WHERE id = ?", (contact_id,))
            row = cursor.fetchone()
            return self._row_to_contact(row) if row else None

    def delete_contact(self, contact_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM th_contacts WHERE id = ?", (contact_id,))
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_contact(self, r: sqlite3.Row) -> PrivateContact:
        return PrivateContact(
            id=r["id"],
            tenant_id=r["tenant_id"],
            name=r["name"],
            country=r["country"],
            city=r["city"] or "",
            role=TradeRole(r["role"]) if r["role"] in TradeRole.__members__ else TradeRole.BOTH,
            contact_person=r["contact_person"] or "",
            email=r["email"] or "",
            phone=r["phone"] or "",
            website=r["website"] or "",
            address=r["address"] or "",
            products=json.loads(r["products_json"] or "[]"),
            hs_codes=json.loads(r["hs_codes_json"] or "[]"),
            capacity_monthly=r["capacity_monthly"] or "",
            moq=r["moq"],
            unit_price_usd=Decimal(str(r["unit_price_usd"])) if r["unit_price_usd"] is not None else None,
            price_validity_date=r["price_validity_date"],
            payment_terms=r["payment_terms"] or "T/T",
            incoterms=GlobalIncoterms(r["incoterms"]) if r["incoterms"] in GlobalIncoterms.__members__ else GlobalIncoterms.FOB,
            lead_time_days=r["lead_time_days"],
            certifications=json.loads(r["certifications_json"] or "[]"),
            source_reference=r["source_reference"] or "Manual Entry",
            verification_status=VerificationStatus(r["verification_status"]) if r["verification_status"] in VerificationStatus.__members__ else VerificationStatus.PRELIMINARY_MATCH,
            private_notes=r["private_notes"] or "",
            tags=json.loads(r["tags_json"] or "[]"),
            created_at=r["created_at"],
            updated_at=r["updated_at"]
        )

    # ----------------------------------------------------------------------
    # RFQ Operations
    # ----------------------------------------------------------------------

    def create_rfq(self, rfq: RFQRecord) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO th_rfqs (
                    tenant_id, rfq_type, status, title, product_name, hs_code,
                    origin_country, target_country, target_quantity, unit,
                    target_price_usd, incoterms, payment_terms, deadline_date,
                    contact_id, contact_name, evidence_source, specs_summary, notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rfq.tenant_id, rfq.rfq_type.value, rfq.status.value, rfq.title.strip(),
                rfq.product_name.strip(), rfq.hs_code, rfq.origin_country, rfq.target_country,
                float(rfq.target_quantity), rfq.unit,
                float(rfq.target_price_usd) if rfq.target_price_usd is not None else None,
                rfq.incoterms.value, rfq.payment_terms, rfq.deadline_date,
                rfq.contact_id, rfq.contact_name, rfq.evidence_source,
                rfq.specs_summary, rfq.notes, now, now
            ))
            conn.commit()
            return cursor.lastrowid

    def save_rfq(self, rfq: RFQRecord) -> int:
        return self.create_rfq(rfq)

    def get_rfq_by_id(self, rfq_id: int, tenant_id: str = "default_importer") -> Optional[RFQRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM th_rfqs WHERE id = ? AND tenant_id = ?", (rfq_id, tenant_id))
            row = cursor.fetchone()
            return self._row_to_rfq(row) if row else None

    def update_rfq_status(self, rfq_id: int, status: RFQStatus, notes: Optional[str] = None, tenant_id: str = "default_importer") -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if notes is not None:
                cursor.execute("""
                    UPDATE th_rfqs
                    SET status = ?, notes = ?, updated_at = ?
                    WHERE id = ? AND tenant_id = ?
                """, (status.value, notes, now, rfq_id, tenant_id))
            else:
                cursor.execute("""
                    UPDATE th_rfqs
                    SET status = ?, updated_at = ?
                    WHERE id = ? AND tenant_id = ?
                """, (status.value, now, rfq_id, tenant_id))
            conn.commit()
            return cursor.rowcount > 0

    def list_rfqs(
        self,
        status: Optional[RFQStatus] = None,
        rfq_type: Optional[RFQType] = None,
        tenant_id: str = "default_importer",
        limit: int = 100
    ) -> List[RFQRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM th_rfqs WHERE tenant_id = ?"
            params: List[Any] = [tenant_id]

            if status:
                query += " AND status = ?"
                params.append(status.value)
            if rfq_type:
                query += " AND rfq_type = ?"
                params.append(rfq_type.value)

            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_rfq(r) for r in rows]

    def _row_to_rfq(self, r: sqlite3.Row) -> RFQRecord:
        return RFQRecord(
            id=r["id"],
            tenant_id=r["tenant_id"],
            rfq_type=RFQType(r["rfq_type"]),
            status=RFQStatus(r["status"]),
            title=r["title"],
            product_name=r["product_name"],
            hs_code=r["hs_code"],
            origin_country=r["origin_country"],
            target_country=r["target_country"],
            target_quantity=Decimal(str(r["target_quantity"])),
            unit=r["unit"],
            target_price_usd=Decimal(str(r["target_price_usd"])) if r["target_price_usd"] is not None else None,
            incoterms=GlobalIncoterms(r["incoterms"]),
            payment_terms=r["payment_terms"],
            deadline_date=r["deadline_date"],
            contact_id=r["contact_id"],
            contact_name=r["contact_name"],
            evidence_source=r["evidence_source"],
            specs_summary=r["specs_summary"] or "",
            notes=r["notes"] or "",
            created_at=r["created_at"],
            updated_at=r["updated_at"]
        )

    # ----------------------------------------------------------------------
    # Deal Management Operations
    # ----------------------------------------------------------------------

    def create_deal(self, deal: DealRecord) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO th_deals (
                    tenant_id, deal_title, stage, rfq_id, buyer_name, supplier_name,
                    product_name, hs_code, quantity, unit, contract_value_usd,
                    estimated_cost_usd, estimated_profit_usd, profit_margin_pct,
                    origin_country, destination_country, incoterms, assigned_to,
                    next_action, next_followup_date, win_loss_reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                deal.tenant_id, deal.deal_title.strip(), deal.stage.value, deal.rfq_id,
                deal.buyer_name.strip(), deal.supplier_name.strip(), deal.product_name.strip(),
                deal.hs_code, float(deal.quantity), deal.unit,
                float(deal.contract_value_usd), float(deal.estimated_cost_usd),
                float(deal.estimated_profit_usd), float(deal.profit_margin_pct),
                deal.origin_country, deal.destination_country, deal.incoterms.value,
                deal.assigned_to, deal.next_action, deal.next_followup_date,
                deal.win_loss_reason, now, now
            ))
            conn.commit()
            return cursor.lastrowid

    def save_deal(self, deal: DealRecord) -> int:
        return self.create_deal(deal)

    def get_deal_by_id(self, deal_id: int, tenant_id: str = "default_importer") -> Optional[DealRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM th_deals WHERE id = ? AND tenant_id = ?", (deal_id, tenant_id))
            row = cursor.fetchone()
            return self._row_to_deal(row) if row else None

    def list_deals(
        self,
        stage: Optional[DealStage] = None,
        tenant_id: str = "default_importer",
        limit: int = 100
    ) -> List[DealRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM th_deals WHERE tenant_id = ?"
            params: List[Any] = [tenant_id]

            if stage:
                query += " AND stage = ?"
                params.append(stage.value)

            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_deal(r) for r in rows]

    def update_deal_stage(
        self,
        deal_id: int,
        new_stage: Optional[DealStage] = None,
        stage: Optional[DealStage] = None,
        next_action: Optional[str] = None,
        next_followup_date: Optional[str] = None,
        win_loss_reason: Optional[str] = None,
        tenant_id: str = "default_importer"
    ) -> bool:
        target_stage = new_stage or stage
        if not target_stage:
            return False
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE th_deals
                SET stage = ?,
                    next_action = COALESCE(?, next_action),
                    next_followup_date = COALESCE(?, next_followup_date),
                    win_loss_reason = COALESCE(?, win_loss_reason),
                    updated_at = ?
                WHERE id = ? AND tenant_id = ?
            """, (target_stage.value, next_action, next_followup_date, win_loss_reason, now, deal_id, tenant_id))
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_deal(self, r: sqlite3.Row) -> DealRecord:
        return DealRecord(
            id=r["id"],
            tenant_id=r["tenant_id"],
            deal_title=r["deal_title"],
            stage=DealStage(r["stage"]),
            rfq_id=r["rfq_id"],
            buyer_name=r["buyer_name"],
            supplier_name=r["supplier_name"],
            product_name=r["product_name"],
            hs_code=r["hs_code"],
            quantity=Decimal(str(r["quantity"])),
            unit=r["unit"],
            contract_value_usd=Decimal(str(r["contract_value_usd"])),
            estimated_cost_usd=Decimal(str(r["estimated_cost_usd"])),
            estimated_profit_usd=Decimal(str(r["estimated_profit_usd"])),
            profit_margin_pct=Decimal(str(r["profit_margin_pct"])),
            origin_country=r["origin_country"],
            destination_country=r["destination_country"],
            incoterms=GlobalIncoterms(r["incoterms"]),
            assigned_to=r["assigned_to"] or "Trade Manager",
            next_action=r["next_action"] or "",
            next_followup_date=r["next_followup_date"],
            win_loss_reason=r["win_loss_reason"],
            created_at=r["created_at"],
            updated_at=r["updated_at"]
        )

    # ----------------------------------------------------------------------
    # Trade Records (Statistical Data)
    # ----------------------------------------------------------------------

    def save_trade_record(self, rec: NormalizedTradeRecord) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO th_trade_records (
                    source_id, source_name, source_url, external_record_id,
                    retrieved_at, published_at, data_period, country_origin,
                    country_destination, hs_code, product_title_en, product_title_fa,
                    trade_value_usd, trade_quantity, quantity_unit, unit_value_usd,
                    annual_growth_rate_pct, market_share_pct, evidence_type,
                    confidence_level, is_mirror_data, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec.source_id, rec.source_name, rec.source_url, rec.external_record_id,
                rec.retrieved_at, rec.published_at, rec.data_period, rec.country_origin,
                rec.country_destination, rec.hs_code, rec.product_title_en, rec.product_title_fa,
                float(rec.trade_value_usd),
                float(rec.trade_quantity) if rec.trade_quantity is not None else None,
                rec.quantity_unit,
                float(rec.unit_value_usd) if rec.unit_value_usd is not None else None,
                float(rec.annual_growth_rate_pct) if rec.annual_growth_rate_pct is not None else None,
                float(rec.market_share_pct) if rec.market_share_pct is not None else None,
                rec.evidence_type.value, rec.confidence_level.value,
                1 if rec.is_mirror_data else 0, rec.notes
            ))
            conn.commit()
            return cursor.lastrowid

    def query_trade_records(
        self,
        hs_code: Optional[str] = None,
        country: Optional[str] = None,
        period: Optional[str] = None,
        limit: int = 50
    ) -> List[NormalizedTradeRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM th_trade_records WHERE 1=1"
            params: List[Any] = []

            if hs_code:
                clean_hs = hs_code.replace(".", "").strip()
                query += " AND hs_code LIKE ?"
                params.append(f"{clean_hs}%")

            if country:
                query += " AND (country_origin LIKE ? OR country_destination LIKE ?)"
                params.extend([f"%{country}%", f"%{country}%"])

            if period:
                query += " AND data_period = ?"
                params.append(period)

            query += " ORDER BY trade_value_usd DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_trade_record(r) for r in rows]

    def _row_to_trade_record(self, r: sqlite3.Row) -> NormalizedTradeRecord:
        return NormalizedTradeRecord(
            source_id=r["source_id"],
            source_name=r["source_name"],
            source_url=r["source_url"] or "",
            external_record_id=r["external_record_id"],
            retrieved_at=r["retrieved_at"],
            published_at=r["published_at"],
            data_period=r["data_period"],
            country_origin=r["country_origin"],
            country_destination=r["country_destination"],
            hs_code=r["hs_code"],
            product_title_en=r["product_title_en"] or "",
            product_title_fa=r["product_title_fa"] or "",
            trade_value_usd=Decimal(str(r["trade_value_usd"])),
            trade_quantity=Decimal(str(r["trade_quantity"])) if r["trade_quantity"] is not None else None,
            quantity_unit=r["quantity_unit"] or "Tons",
            unit_value_usd=Decimal(str(r["unit_value_usd"])) if r["unit_value_usd"] is not None else None,
            annual_growth_rate_pct=Decimal(str(r["annual_growth_rate_pct"])) if r["annual_growth_rate_pct"] is not None else None,
            market_share_pct=Decimal(str(r["market_share_pct"])) if r["market_share_pct"] is not None else None,
            evidence_type=EvidenceType(r["evidence_type"]),
            confidence_level=ConfidenceLevel(r["confidence_level"]),
            is_mirror_data=bool(r["is_mirror_data"]),
            notes=r["notes"] or ""
        )

    # ----------------------------------------------------------------------
    # Market Dossiers
    # ----------------------------------------------------------------------

    def save_dossier(self, dossier_type: str, query_title: str, data: Dict[str, Any], hs_code: str = "", country: str = "") -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO th_market_dossiers (dossier_type, query_title, hs_code, country, dossier_json)
                VALUES (?, ?, ?, ?, ?)
            """, (dossier_type, query_title, hs_code, country, json.dumps(data, ensure_ascii=False)))
            conn.commit()
            return cursor.lastrowid

    def get_recent_dossiers(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, dossier_type, query_title, hs_code, country, created_at FROM th_market_dossiers ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def log_audit(self, action: str, entity_type: str, entity_id: Optional[int], details: str, tenant_id: str = "default_importer"):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO th_audit_logs (tenant_id, action, entity_type, entity_id, details)
                VALUES (?, ?, ?, ?, ?)
            """, (tenant_id, action, entity_type, entity_id, details))
            conn.commit()
