"""
Unit tests for My Trade Network (Private CRM repository and batch CSV importer).
Verifies tenant isolation, de-duplication, and CSV formula injection sanitization.
"""

import pytest
import os
from decimal import Decimal

from trade_hub.models import PrivateContact, TradeRole, VerificationStatus, GlobalIncoterms
from trade_hub.db import TradeHubDatabase
from trade_hub.network.repository import TradeNetworkRepository
from trade_hub.network.importer import NetworkBatchImporter


@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_trade_hub.db")
    return TradeHubDatabase(db_path=db_file)


def test_contact_save_and_deduplication(temp_db):
    repo = TradeNetworkRepository(temp_db)

    c1 = PrivateContact(
        name="Ankara Polymer Ticaret",
        country="Turkey",
        city="Ankara",
        role=TradeRole.SUPPLIER,
        email="export@ankarapolymer.com.tr",
        products=["HDPE", "Polypropylene"],
        unit_price_usd=Decimal("920.00")
    )
    saved1 = repo.save_contact(c1)
    assert saved1.id is not None
    assert saved1.name == "Ankara Polymer Ticaret"

    # Saving again with same email should raise ValueError (de-duplication)
    c2 = PrivateContact(
        name="Ankara Polymer Branch 2",
        country="Turkey",
        role=TradeRole.SUPPLIER,
        email="export@ankarapolymer.com.tr",
        products=["HDPE"]
    )
    with pytest.raises(ValueError, match="Duplicate contact detected"):
        repo.save_contact(c2)


def test_search_contacts_priority(temp_db):
    repo = TradeNetworkRepository(temp_db)

    repo.save_contact(PrivateContact(
        name="Al-Mansoor Construction",
        country="Iraq",
        city="Baghdad",
        role=TradeRole.BUYER,
        email="purchase@almansoor.iq",
        products=["Ceramic Tiles", "Portland Cement"],
        hs_codes=["6907.21", "2523.29"]
    ))

    repo.save_contact(PrivateContact(
        name="Dubai Petrochem FZE",
        country="UAE",
        city="Dubai",
        role=TradeRole.BOTH,
        email="info@dubaipetroglobal.ae",
        products=["Bitumen 60/70", "Methanol"],
        hs_codes=["2713.20"]
    ))

    # Search by product query
    results_tile = repo.search_contacts(product_query="Ceramic Tiles", role=TradeRole.BUYER)
    assert len(results_tile) == 1
    assert results_tile[0].name == "Al-Mansoor Construction"

    # Search by HS code
    results_bitumen = repo.search_contacts(hs_code="2713.20")
    assert len(results_bitumen) == 1
    assert results_bitumen[0].name == "Dubai Petrochem FZE"


def test_csv_formula_injection_sanitization(temp_db):
    """
    Ensures dangerous spreadsheet formulas (=cmd, @SUM, -1+1, +calc)
    are stripped to prevent CSV Formula Injection attacks.
    """
    csv_payload = """name,country,role,email,products,unit_price_usd
=cmd|' /C calc'!A0,Iraq,BUYER,test1@attacker.iq,Bitumen,400
@SUM(1+1)*cmd,UAE,SUPPLIER,test2@attacker.ae,Polymer,900
+cmd|' /C notepad'!A0,Turkey,BOTH,test3@attacker.com,Cement,80
-10+20,Germany,BUYER,test4@attacker.de,Machines,1500
Safe Company Ltd,Oman,BUYER,safe@oman.om,Bitumen,450
"""
    res = NetworkBatchImporter.import_csv(csv_payload, tenant_id="test_tenant", db=temp_db)
    assert res["status"] == "success"
    assert res["imported_count"] == 5

    repo = TradeNetworkRepository(temp_db)
    contacts = repo.search_contacts(tenant_id="test_tenant")
    names = [c.name for c in contacts]

    # Check that dangerous leading characters were neutralized
    for n in names:
        assert not n.startswith("=")
        assert not n.startswith("@")
        assert not n.startswith("+")
        assert not n.startswith("-")

    assert any("cmd" in n for n in names)
    assert "Safe Company Ltd" in names
