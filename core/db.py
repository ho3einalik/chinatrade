"""
Database persistence engine for iTrade China using SQLite.
Stores search queries, audit snapshots, supplier quotations, price history, and price alerts.
Includes schema migration and thread-safe operations.
"""

import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

DB_FILE = os.environ.get("ITRADE_DB_PATH", "itrade.db")

class Database:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Search history
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                status TEXT DEFAULT 'COMPLETED',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 2. Audit snapshots
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id INTEGER,
                query TEXT NOT NULL,
                rule_version TEXT NOT NULL,
                report_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (search_id) REFERENCES search_history(id)
            )
            """)

            # 3. Supplier quotations (both crawled & manual)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id INTEGER,
                supplier_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                product_title TEXT NOT NULL,
                unit_price_cny REAL NOT NULL,
                moq INTEGER DEFAULT 1,
                is_manual BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (search_id) REFERENCES search_history(id)
            )
            """)

            # 4. Price history for trends
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_title TEXT NOT NULL,
                platform TEXT NOT NULL,
                price_toman REAL NOT NULL,
                sample_count INTEGER DEFAULT 1,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # 5. Price & Profit Alerts
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_product TEXT NOT NULL,
                threshold_profit_toman REAL NOT NULL,
                user_contact TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            conn.commit()

    def save_search_and_snapshot(self, query: str, category: str, report_dict: Dict[str, Any], rule_version: str) -> int:
        """Saves search record and full audit snapshot, returning snapshot ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO search_history (query, category, status) VALUES (?, ?, ?)",
                (query, category, "COMPLETED")
            )
            search_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO audit_snapshots (search_id, query, rule_version, report_data) VALUES (?, ?, ?, ?)",
                (search_id, query, rule_version, json.dumps(report_dict, ensure_ascii=False))
            )
            snapshot_id = cursor.lastrowid
            conn.commit()
            return snapshot_id

    def get_recent_snapshots(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent audit snapshots."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, search_id, query, rule_version, created_at FROM audit_snapshots ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_snapshot_by_id(self, snapshot_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves full snapshot data by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_snapshots WHERE id = ?", (snapshot_id,))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                d["report_data"] = json.loads(d["report_data"])
                return d
            return None

    def save_manual_quote(self, search_id: Optional[int], name: str, platform: str, title: str, price_cny: float, moq: int) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO supplier_quotes (search_id, supplier_name, platform, product_title, unit_price_cny, moq, is_manual)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (search_id, name, platform, title, price_cny, moq))
            conn.commit()
            return cursor.lastrowid

    def record_market_price(self, title: str, platform: str, price_toman: float, count: int = 1):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO price_history (product_title, platform, price_toman, sample_count)
                VALUES (?, ?, ?, ?)
            """, (title, platform, price_toman, count))
            conn.commit()

    def create_price_alert(self, product_name: str, threshold_profit_toman: float, user_contact: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO price_alerts (target_product, threshold_profit_toman, user_contact, is_active)
                VALUES (?, ?, ?, 1)
            """, (product_name, threshold_profit_toman, user_contact))
            conn.commit()
            return cursor.lastrowid

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM price_alerts WHERE is_active = 1")
            return [dict(r) for r in cursor.fetchall()]
