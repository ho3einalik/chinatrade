"""
Unit tests for the 3 Trade Intelligence Journeys, Company Verification, and AI Assistant.
"""

from decimal import Decimal
import pytest

from trade_hub.db import TradeHubDatabase
from trade_hub.sources.registry import TradeSourcesRegistry
from trade_hub.network.repository import TradeNetworkRepository
from trade_hub.models import PrivateContact, TradeRole, VerificationStatus, GlobalIncoterms
from trade_hub.intelligence.journey_seller import SellerJourneyEngine
from trade_hub.intelligence.journey_buyer import BuyerJourneyEngine
from trade_hub.intelligence.journey_discovery import DiscoveryJourneyEngine
from trade_hub.intelligence.company_verification import CompanyVerificationEngine
from trade_hub.intelligence.ai_assistant import TradeAIAssistant


@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_journeys.db")
    return TradeHubDatabase(db_path=db_file)


def test_journey_seller_bitumen_execution(temp_db):
    registry = TradeSourcesRegistry()
    network_repo = TradeNetworkRepository(temp_db)

    # Seed a private buyer
    network_repo.save_contact(PrivateContact(
        name="Gulf Asphalt Trading LLC",
        country="Oman",
        role=TradeRole.BUYER,
        email="procurement@gulfasphalt.om",
        products=["Bitumen 60/70"],
        hs_codes=["2713.20"]
    ))

    engine = SellerJourneyEngine(db=temp_db, registry=registry, network_repo=network_repo)
    dossier = engine.execute(
        product_name="قیر ۶۰/۷۰",
        origin_country="Iran",
        target_country="Oman",
        unit_cost_usd=Decimal("370.00"),
        batch_quantity=Decimal("500")
    )

    assert dossier.hs_code_primary == "2713.20"
    assert len(dossier.top_importing_countries) > 0
    assert len(dossier.candidate_buyers) > 0
    # Private network contact should be present
    assert any(b.is_private_network for b in dossier.candidate_buyers)
    assert len(dossier.action_roadmap) == 5
    assert len(dossier.draft_sales_pitch_en) > 50
    assert len(dossier.draft_sales_pitch_fa) > 50
    assert dossier.data_confidence_score > 80.0


def test_journey_buyer_hdpe_execution(temp_db):
    registry = TradeSourcesRegistry()
    network_repo = TradeNetworkRepository(temp_db)

    # Seed a private supplier
    network_repo.save_contact(PrivateContact(
        name="Istanbul Polymer Sanayi",
        country="Turkey",
        role=TradeRole.SUPPLIER,
        email="export@istanbulpolymer.tr",
        products=["HDPE Film Grade"],
        unit_price_usd=Decimal("940.00"),
        incoterms=GlobalIncoterms.FOB
    ))

    engine = BuyerJourneyEngine(db=temp_db, registry=registry, network_repo=network_repo)
    dossier = engine.execute(
        product_name="پلی‌اتیلن سنگین HDPE",
        origin_country_preference="Turkey",
        destination_country="Iran",
        batch_quantity=Decimal("200")
    )

    assert dossier.private_network_hits_count == 1
    assert len(dossier.candidate_suppliers) > 0
    assert dossier.candidate_suppliers[0].is_private_network is True
    assert dossier.estimated_landed_cost is not None
    assert dossier.estimated_landed_cost.total_landed_cost_per_unit_usd > Decimal("940.00")
    assert dossier.data_confidence_score >= 90.0


def test_journey_discovery_demand_radar(temp_db):
    registry = TradeSourcesRegistry()
    engine = DiscoveryJourneyEngine(db=temp_db, registry=registry)

    # Test all sectors
    dossier_all = engine.execute(sector="all", min_growth_pct=4.0)
    assert len(dossier_all.discovered_opportunities) > 0
    assert len(dossier_all.untapped_export_potential_markets) > 0

    # Test specific petrochemicals sector
    dossier_petro = engine.execute(sector="petrochemicals", min_growth_pct=5.0)
    assert all("hs_code" in p for p in dossier_petro.discovered_opportunities)
    assert len(dossier_petro.discovered_opportunities) >= 2


def test_company_verification_engine():
    # Legitimate corporate entity
    clean_contact = PrivateContact(
        name="Vanguard Chemicals GMBH",
        country="Germany",
        city="Frankfurt",
        email="export@vanguardchem.de",
        website="https://vanguardchem.de",
        address="Industriestrasse 42, 60311 Frankfurt",
        payment_terms="L/C at sight 100%",
        certifications=["ISO 9001", "REACH Certificate"]
    )
    res_clean = CompanyVerificationEngine.evaluate_contact(clean_contact)
    assert res_clean["status"] == VerificationStatus.OFFICIAL_VERIFIED
    assert res_clean["verification_score"] >= 80
    assert res_clean["is_cleared_for_negotiation"] is True

    # High-risk entity with red flags
    risky_contact = PrivateContact(
        name="Fast Profit Global Anonymous",
        country="Offshore Island",
        email="moneytransfer123@gmail.com",
        payment_terms="100% advance western union to personal account",
        private_notes="no invoice available third party transfer only"
    )
    res_risky = CompanyVerificationEngine.evaluate_contact(risky_contact)
    assert res_risky["status"] == VerificationStatus.RED_FLAG
    assert len(res_risky["alerts"]) >= 2
    assert res_risky["is_cleared_for_negotiation"] is False


def test_trade_ai_assistant():
    pitches = TradeAIAssistant.generate_export_sales_pitch(
        company_name="Iran Bitumen Export Corp",
        product_name_en="Petroleum Bitumen 60/70",
        product_name_fa="قیر ۶۰/۷۰",
        hs_code="2713.20",
        target_country="India",
        unit_price_usd=Decimal("390.00"),
        incoterms=GlobalIncoterms.FOB
    )
    assert "2713.20" in pitches["pitch_en"]
    assert "India" in pitches["pitch_en"]
    assert "FOB" in pitches["pitch_en"]
    assert "قیر ۶۰/۷۰" in pitches["pitch_fa"]

    rfq_letter = TradeAIAssistant.generate_formal_rfq_letter(
        importer_name="Tehran Industrial Supplies",
        supplier_name="Global Steel Traders",
        product_name="Cold Rolled Steel Coil",
        hs_code="7209.16",
        quantity=Decimal("1500"),
        unit="Tons"
    )
    assert "FORMAL REQUEST FOR QUOTATION" in rfq_letter
    assert "7209.16" in rfq_letter
    assert "1,500.00 Tons" in rfq_letter
