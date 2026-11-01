"""
MANDATORY ARCHITECTURAL ISOLATION TEST:
Verifies 100% physical and logical data isolation between
China Import Module (itrade.db) and Trade Intelligence Hub (trade_hub.db).
Zero cross-contamination or unauthorized data leakage.
"""

import sqlite3
import os
import pytest
from decimal import Decimal

from core.db import Database as ChinaImportDatabase, DB_FILE as CHINA_DB_PATH
from trade_hub.db import TradeHubDatabase, DEFAULT_TRADE_DB_PATH
from trade_hub.models import PrivateContact, TradeRole, RFQRecord, GlobalIncoterms


CHINA_TABLES = {"search_history", "supplier_quotes", "audit_snapshots", "price_history", "price_alerts"}
TRADE_HUB_TABLES = {"th_contacts", "th_rfqs", "th_deals", "th_trade_records", "th_market_dossiers", "th_audit_logs"}


def get_sqlite_tables(db_path: str) -> set:
    if not os.path.exists(db_path):
        return set()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()
    return tables


def test_physical_database_file_isolation():
    """
    Ensures that the two database file paths are completely distinct.
    """
    assert CHINA_DB_PATH != DEFAULT_TRADE_DB_PATH
    assert os.path.basename(CHINA_DB_PATH) == "itrade.db"
    assert os.path.basename(DEFAULT_TRADE_DB_PATH) == "trade_hub.db"


def test_schema_isolation(tmp_path):
    """
    Ensures that neither database contains tables from the other module.
    """
    china_db_file = str(tmp_path / "itrade_isolated.db")
    trade_db_file = str(tmp_path / "trade_hub_isolated.db")

    china_db = ChinaImportDatabase(db_path=china_db_file)
    trade_db = TradeHubDatabase(db_path=trade_db_file)

    china_tables = get_sqlite_tables(china_db_file)
    trade_tables = get_sqlite_tables(trade_db_file)

    # 1. Check China tables are present in China DB and absent in Trade Hub DB
    for tbl in CHINA_TABLES:
        assert tbl in china_tables, f"Expected table {tbl} in China Import DB"
        assert tbl not in trade_tables, f"Forbidden table {tbl} found in Trade Hub DB!"

    # 2. Check Trade Hub tables are present in Trade Hub DB and absent in China DB
    for tbl in TRADE_HUB_TABLES:
        assert tbl in trade_tables, f"Expected table {tbl} in Trade Hub DB"
        assert tbl not in china_tables, f"Forbidden table {tbl} found in China Import DB!"


def test_runtime_data_write_isolation(tmp_path):
    """
    Verifies that inserting data into Trade Hub has zero side-effects on China Import, and vice-versa.
    """
    china_db_file = str(tmp_path / "itrade_write_test.db")
    trade_db_file = str(tmp_path / "trade_hub_write_test.db")

    china_db = ChinaImportDatabase(db_path=china_db_file)
    trade_db = TradeHubDatabase(db_path=trade_db_file)

    # Insert record into Trade Hub
    contact = PrivateContact(
        name="Isolation Test Corp",
        country="Oman",
        role=TradeRole.BUYER,
        email="isolation@oman.om",
        products=["Bitumen"]
    )
    c_id = trade_db.save_contact(contact)
    assert c_id is not None

    rfq = RFQRecord(
        title="Isolation RFQ",
        product_name="Bitumen 60/70",
        origin_country="Iran",
        target_country="Oman"
    )
    r_id = trade_db.save_rfq(rfq)
    assert r_id is not None

    # Inspect China DB: must still have 0 records across all tables
    with sqlite3.connect(china_db_file) as conn:
        cursor = conn.cursor()
        for tbl in CHINA_TABLES:
            cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
            count = cursor.fetchone()[0]
            assert count == 0, f"Cross-contamination detected! Table {tbl} in itrade.db has {count} rows after Trade Hub write."

    # Insert record into China Import
    china_quote_id = china_db.save_manual_quote(
        search_id=None,
        name="Shenzhen Factory Ltd",
        platform="1688",
        title="Smartwatch Ultra",
        price_cny=85.0,
        moq=100
    )
    assert china_quote_id is not None

    # Inspect Trade Hub DB: row count in th_contacts and th_rfqs must be exactly 1 each, no new rows
    with sqlite3.connect(trade_db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM th_contacts")
        assert cursor.fetchone()[0] == 1
        cursor.execute("SELECT COUNT(*) FROM th_rfqs")
        assert cursor.fetchone()[0] == 1
        cursor.execute("SELECT COUNT(*) FROM th_deals")
        assert cursor.fetchone()[0] == 0
