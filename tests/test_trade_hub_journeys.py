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


def test_journey_seller_dynamic_products(temp_db):
    """Verifies that Journey 1 dynamically analyzes any product entered by the user."""
    registry = TradeSourcesRegistry()
    network_repo = TradeNetworkRepository(temp_db)
    engine = SellerJourneyEngine(db=temp_db, registry=registry, network_repo=network_repo)

    # 1. Saffron
    dossier_saffron = engine.execute(product_name="زعفران نگین قائنات")
    assert dossier_saffron.hs_code_primary == "0910.20"
    assert "Spain" in [c.country_destination for c in dossier_saffron.top_importing_countries]
    assert dossier_saffron.export_cost_estimate is not None
    assert any("trademap.org" in src for src in dossier_saffron.sources_cited)

    # 2. Ceramic Tiles
    dossier_tiles = engine.execute(product_name="کاشی پرسلان لعاب‌دار")
    assert dossier_tiles.hs_code_primary == "6907.21"
    assert "Iraq" in [c.country_destination for c in dossier_tiles.top_importing_countries]

    # 3. Urea
    dossier_urea = engine.execute(product_name="کود اوره گرانول")
    assert dossier_urea.hs_code_primary == "3102.10"
    assert "Brazil" in [c.country_destination for c in dossier_urea.top_importing_countries]

    # 4. Steel Rebar
    dossier_steel = engine.execute(product_name="میلگرد آجدار A3")
    assert dossier_steel.hs_code_primary == "7214.20"

    # 5. Explicit HS code in query
    dossier_hs = engine.execute(product_name="صادرات با کد 080251")
    assert dossier_hs.hs_code_primary == "0802.51"

    # 6. Unlisted Agrifood product
    dossier_food = engine.execute(product_name="روغن زیتون فرابکر")
    assert len(dossier_food.top_importing_countries) > 0
    assert len(dossier_food.candidate_buyers) > 0


def test_trademap_adapter_parse_csv_export():
    """Verifies parsing of authentic ITC Trade Map CSV/TSV table export."""
    from trade_hub.sources.trademap import TradeMapAdapter

    sample_trademap_tsv = (
        "Importers\tValue imported in 2023 (USD thousand)\tValue imported in 2024 (USD thousand)\t"
        "Quantity imported in 2024\tUnit value (USD/unit)\tAnnual growth in value between 2020-2024 (%)\tShare in world imports (%)\n"
        "World\t3200000\t3450000\t450000\t7666\t4.5\t100\n"
        "Germany\t450000\t490000\t60000\t8166\t5.2\t14.2\n"
        "China\t380000\t410000\t55000\t7454\t8.1\t11.8\n"
        "United Arab Emirates\t210000\t230000\t32000\t7187\t3.9\t6.6\n"
    )

    records = TradeMapAdapter.parse_csv_export(sample_trademap_tsv, "sample_export.tsv", "0802.51")
    assert len(records) == 3  # "World" excluded
    destinations = [r.country_destination for r in records]
    assert "Germany" in destinations
    assert "China" in destinations
    assert "United Arab Emirates" in destinations

    ger_record = next(r for r in records if r.country_destination == "Germany")
    assert ger_record.trade_value_usd == Decimal("490000000")  # 490,000 * 1000
    assert ger_record.unit_value_usd == Decimal("8166")
    assert ger_record.annual_growth_rate_pct == Decimal("5.2")
    assert ger_record.market_share_pct == Decimal("14.2")


def test_trade_sources_metadata_structure():
    """Ensures that all 7 external trade sources return complete, non-undefined metadata."""
    registry = TradeSourcesRegistry()
    sources = registry.list_sources()

    assert len(sources) == 7
    for s in sources:
        assert s["source_id"]
        assert s["name"]
        assert s["base_url"].startswith("http")
        assert s["operational_status"] in ("ACTIVE_DIRECT", "PORTAL_SEARCH")
        assert len(s["coverage_geography"]) > 0
        assert len(s["coverage_frequency"]) > 0
        assert len(s["notes"]) > 10
        # None of these must ever be undefined/empty
        assert "undefined" not in s["name"].lower()
        assert "undefined" not in s["notes"].lower()
