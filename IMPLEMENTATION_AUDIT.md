# IMPLEMENTATION AUDIT & BASELINE ASSESSMENT
**iTrade China Platform - System & Codebase Audit**
**Date:** 2026-11-01
**Auditor:** Senior Engineering, Architecture, Data, Scraping, Logistics & QA Team

---

## 1. Executive Summary & Baseline State

An exhaustive audit of the existing `iTrade China` codebase was conducted. The system was originally built as a prototype with an initial Streamlit UI (`app.py`), a CLI tool (`cli.py`), and a subsequent FastAPI web service (`server.py`) serving a static single-page frontend (`static/index.html`).

### Baseline Test Execution
- **Command Executed:** `pytest`
- **Result:** `collected 0 items / no tests ran in 0.05s (exit code 1)`
- **Finding:** No automated unit, integration, or regression test suite existed prior to this audit.

---

## 2. Component-by-Component Classification

Every feature in the repository has been evaluated and categorized into one of five rigorous tiers:

| Component / Feature | File Location | Status | Detailed Finding & Deficiencies |
| :--- | :--- | :--- | :--- |
| **Digikala API Client** | `core/iran_market.py` | **Maturity: Incomplete** | Direct API query to `https://api.digikala.com/v1/search/` functions live when internet is connected, but lacks pagination, retry backoff, schema validation, outlier filtering, and outlier-resistant median calculation. |
| **Torob / Emalls / Basalam / Divar** | `core/iran_market.py` | **Maturity: Demo-Only / Mocked** | These channels generate synthetic pricing approximations (e.g. `lowest * 1.03`, `avg * 0.94`) and construct search URLs. They do not parse actual live listings or transactions from these platforms. |
| **Chinese Suppliers Engine** | `core/china_sourcing.py` | **Maturity: Demo-Only / Mocked** | Contains hardcoded sample factory dictionaries for chemicals, gadgets, tools, and general goods. While URLs point to real domains (1688, EHSY, Gongchang, Makepolo, QiPeiRen), pricing tiers and supplier specs are static templates rather than structured extracts. |
| **Landed Cost Calculator** | `core/calculator.py` | **Maturity: Incomplete / Flawed** | Uses IEEE 754 `float` for all monetary arithmetic, causing floating-point rounding errors. Lacks distinction between IRR (Rial) and IRT (Toman). Hardcodes 4% tariff, 11% commercial benefit, and 10% VAT without dated legal rule citation. Lacks line items for demurrage, sample inspection, financing cost, and defect allowances. |
| **Profit & Scenario Engine** | `core/calculator.py` | **Maturity: Incomplete** | Computes only a single deterministic point estimate. Lacks 3-scenario modeling (Optimistic, Realistic, Pessimistic), sensitivity analysis, markup vs margin clarity, and safe handling of zero/negative contribution margins. |
| **Product Matching Engine** | N/A (Missing) | **Maturity: Not Implemented** | No matching engine exists. Searches match by loose string inclusion without attribute extraction (dimensions, weight, power, voltage, materials, packaging, GTIN/MPN), leaving comparisons vulnerable to false equivalences. |
| **Opportunity Ranking** | `core/agent.py` | **Maturity: Incomplete** | Calculates an ad-hoc heuristic score (`opp_score`) heavily biased toward raw margin. Does not isolate data confidence from opportunity score, nor does it factor in capital lockup, supplier default risk, or regulatory barriers. |
| **Supplier Verification** | N/A (Missing) | **Maturity: Demo-Only** | Uses decorative badge strings like `"Verified Super Factory"` without structured entity verification, Chinese legal registration ID checks, credit ratings, or audit trail verification. |
| **Regulatory & HS Code Module** | `core/agent.py` | **Maturity: Incomplete** | Hardcodes four coarse HS code strings (`8517.62.90`, `3904.10.00`, `8467.21.00`, `8543.70.90`) without dynamic tariff books, regulatory dates, or conditional licensing logic. |
| **Data Persistence & History** | N/A (Missing) | **Maturity: Not Implemented** | Zero database persistence. All state is ephemeral in memory. No audit logs, no price trend tracking, no historical snapshots, and no reproducible inputs. |
| **Alerting System** | N/A (Missing) | **Maturity: Not Implemented** | No background scheduler, price change notification, margin drop alert, or connector health watcher. |
| **Security & Safety** | `server.py` | **Maturity: Vulnerable** | No URL validation (vulnerable to SSRF if user-supplied URLs are fetched), no input sanitization, and no rate limiting. |
| **FastAPI Web Service & UI** | `server.py`, `static/index.html` | **Maturity: Working & Tested** | Server runs cleanly on port 8000, serving interactive HTML/JS with live calls to `/api/analyze` and `/api/scan`. Needs deep data wiring to replace demo fields with rigorous audit trails. |
| **Reporting Engine** | `core/report_generator.py` | **Maturity: Working** | Produces Markdown and HTML documents. Needs expansion to support CSV/Excel exports, detailed audit trails, dated sources, and scenario tables. |

---

## 3. External Connectivity & Protocol Verification

Live network probes were executed against candidate platforms:

### Chinese Platforms
1. **EHSY (`https://www.ehsy.com/`):** HTTP 200 OK. Responds with valid MRO catalog data. Verified and operational.
2. **Gongchang (`https://www.gongchang.com/`):** HTTP 200 OK. Comprehensive factory directory. Verified and operational.
3. **Makepolo (`https://www.makepolo.com/`):** HTTP 200 OK. Active B2B marketplace search engine. Verified and operational.
4. **QiPeiRen (`https://www.qipeiren.com/`):** Connection Timeout / Great Firewall Drop. Domestic auto parts portal; drops foreign IP packets without Chinese proxy/WeChat gateway.
5. **Nala (`https://www.nala.com.cn/`):** HTTP 503 / SSL EOF Failure. Public web frontend decommissioned; services migrated to private WeChat miniprograms.
6. **YiwuGo (`https://www.yiwugo.com/`):** HTTP 200 OK. Small commodities hub. Verified and operational.
7. **Baidu B2B (`https://b2b.baidu.com/`):** HTTP 200 OK. Baidu Aicai procurement portal. Verified and operational.
8. **1688 (`https://www.1688.com/`):** Heavily guarded behind Alibaba Anti-Bot / Sliding CAPTCHA and Aliyun WAF. Automated scraping requires residential China sessions/APIs; manual quotation entry and structured search URL generation are necessary fallbacks.

### Iranian Platforms
1. **Digikala (`https://api.digikala.com/v1/search/`):** HTTP 200 OK. Responds with structured JSON listing live products, prices in Rials, seller counts, and IDs. Verified and live.
2. **Torob (`https://torob.com/`):** Returns HTTP 490 Anti-Bot Challenge on direct automated scraping without dedicated proxy; deep linking and fallback models required.
3. **Emalls (`https://emalls.ir/`):** Functional for user redirection and deep linking.
4. **Basalam (`https://basalam.com/`):** Search URLs accessible; direct scraping requires token authorization.

---

## 4. Phase-by-Phase Remediation Roadmap

- **Phase A (Now Complete):** Baseline audit and documentation.
- **Phase B:** Core data structures, precision `Decimal` monetary classes, statistical outlier filtration (IQR & trimmed median).
- **Phase C:** Multi-dimensional product matching engine with attribute extraction, schema validation, and explainable scoring.
- **Phase D:** Comprehensive landed cost engine with rule versioning, dated tariff tables, line-item attribution, and 3-scenario Monte Carlo/sensitivity analysis.
- **Phase E:** Robust connectors architecture (Circuit breakers, retry backoffs, structured fallbacks, manual CSV/JSON data ingestion).
- **Phase F:** Multi-factor opportunity scoring, supplier verification framework, and import regulatory constraints checking.
- **Phase G:** Persistent SQLite database (schema, migrations, snapshots, audit log), background alert runner, Excel/CSV exporters, and UI enhancement.
- **Phase H:** 100% passing test suite (Unit, Integration, E2E) and final documentation verification.
