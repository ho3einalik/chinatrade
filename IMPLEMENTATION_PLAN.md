# IMPLEMENTATION PLAN & SYSTEM ARCHITECTURE
**iTrade China - Comprehensive Engineering & Upgrade Plan**
**Date:** 2026-11-01
**Target Architecture:** Clean Architecture (Domain, Core Logic, Connectors, Persistence, Presentation)

---

## 1. Architectural Blueprint

```
import/
├── core/
│   ├── __init__.py
│   ├── models.py              # Pydantic v2 domain schemas with Decimal, enums, & confidence metrics
│   ├── money.py               # Precision Decimal currency conversions (IRR, IRT, CNY, USD, AED)
│   ├── matching.py            # Phase C: Multi-dimensional Product Matching Engine & Attribute Extractor
│   ├── calculator.py          # Phase D: Landed Cost Engine, Rule Versioning, 3 Scenarios, Break-Even
│   ├── ranking.py             # Phase F: Multi-factor Opportunity Ranking (Confidence vs Opportunity)
│   ├── verification.py        # Phase F: Supplier Legitimacy & Chinese Corporate Registry Verification
│   ├── regulations.py         # Phase F: HS Code Candidate Mapping, ISIRI Standards, & License Check
│   ├── db.py                  # Phase G: SQLite Database, Schema Migrations, Snapshots, & Alert Storage
│   ├── alerts.py              # Phase G: Background Alert Job Runner & Price Volatility Trigger
│   ├── report_generator.py    # Phase G: Dossier Exporter (Markdown, Interactive HTML, & Excel)
│   ├── agent.py               # Orchestration Agent unifying all pipelines
│   ├── china_sourcing.py      # Upgraded China Connector Hub with Rate Limiting & Fallback
│   └── iran_market.py         # Upgraded Iran Market Engine with Outlier Removal & Median Analysis
├── connectors/                # Dedicated connectors with timeouts, retries, and schema validation
│   ├── __init__.py
│   ├── base.py                # Abstract Base Connector & Circuit Breaker
│   ├── digikala.py            # Live Digikala API Connector
│   ├── china_b2b.py           # Multi-platform Chinese B2B Connector (EHSY, Gongchang, Makepolo, 1688)
│   └── manual_entry.py        # Manual / CSV / Excel Sourcing Ingestion
├── server.py                  # FastAPI server with SSRF protection, full REST API, & DB persistence
├── static/
│   └── index.html             # Enhanced Dribbble-style UI with interactive channels, matching, & scenarios
├── cli.py                     # Rich CLI with scenario analysis & manual inputs
├── tests/                     # 100% Automated Pytest Suite
│   ├── __init__.py
│   ├── test_money.py          # Unit tests for Decimal conversions and rounding
│   ├── test_matching.py       # Unit tests for product attribute extraction and similarity scoring
│   ├── test_calculator.py     # Unit tests for Landed Cost, customs duty, VAT, and 3 scenarios
│   ├── test_ranking.py        # Unit tests for multi-factor opportunity and confidence separation
│   ├── test_db.py             # Unit tests for SQLite persistence, migrations, and snapshots
│   ├── test_connectors.py     # Integration tests with real and mock responses
│   └── test_e2e.py            # End-to-end integration test from search query to report export
├── config.py                  # Environment-driven, source-cited baseline trade configurations
├── requirements.txt           # Verified dependencies
└── docs/                      # Final Documentation
```

---

## 2. Risk Management & Mitigations

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Floating Point Rounding in Financials** | High (Financial discrepancy, audit failure) | Replace all monetary values with Python's standard `Decimal` class with explicit rounding (`ROUND_HALF_UP`) and strict distinction between Iranian Rial (IRR) and Toman (IRT). |
| **External Anti-Bot / CAPTCHA Blocking** | High (1688, Torob, QiPeiRen block direct scrape) | Implement Graceful Degradation: when live network probes hit anti-bot or network timeouts, flag source status honestly, provide structured direct search deep links, and allow manual quotation / CSV entry without stopping analysis. Never fake a live result. |
| **SSRF (Server-Side Request Forgery)** | Critical (Internal infrastructure exposure) | Implement an explicit SSRF validator: restrict all outgoing requests to public HTTP/HTTPS ports (80, 443), prohibit loopback (127.0.0.1, localhost), private IP ranges (RFC 1918), and link-local / cloud metadata endpoints (169.254.169.254). |
| **False Equivalences in Product Comparison** | High (Misleading margin calculations) | Implement a formal 4-tier match classifier (Exact, Close with differences, Weak, Insufficient Data) with explainable positive/negative attribute vectors and confidence scoring. |
| **Arbitrary Hardcoded Tariff & Shipping Rules** | Medium (Rigid, outdated assumptions) | Move all customs duties (tariffs, commercial benefit, VAT, clearance) and freight rates into configurable, dated rule objects with source attribution and manual override capabilities. |

---

## 3. Execution Schedule & Milestones

1. **Phase B (Data Models & Precision Math):** Create `core/money.py`, upgrade `core/models.py` with `Decimal` and rich schema definitions, implement IQR outlier filtering.
2. **Phase C (Product Matching Engine):** Build `core/matching.py` with standardized attribute schemas, text normalization, and explainable scoring.
3. **Phase D (Landed Cost Engine & 3 Scenarios):** Build `core/calculator.py` with pure `Decimal` arithmetic, dated rule versions, line-item attribution, break-even unit calculation, and sensitivity matrix.
4. **Phase E (Connectors & Safe Fallbacks):** Build `connectors/` with circuit breakers, timeouts, rate limiters, live Digikala parser, and manual CSV/Excel importer.
5. **Phase F (Ranking, Verification & Regulations):** Build `core/ranking.py`, `core/verification.py`, and `core/regulations.py`.
6. **Phase G (Persistence, Alerts, Reports & UI):** Build `core/db.py` (SQLite), `core/alerts.py`, and wire endpoints in `server.py` and `static/index.html`.
7. **Phase H (Test Suite & Final Documentation):** Implement full test suite in `tests/`, verify all tests pass, and generate all 8 mandatory markdown documentation artifacts.
