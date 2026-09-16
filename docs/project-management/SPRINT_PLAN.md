# Sprint Execution Plan: CPMS Autonomous Parking Redemption

**Total Scope:** 4 Sprints (81 Story Points)  
**Methodology:** Agile / Phased Pipeline Gate  
**Reference Specs:** `docs/architecture/system-design.md`, `docs/architecture/concurrency-and-voucher-pool.md`, `docs/adr/ADR-001-vision-extraction-engine.md`, `docs/openapi.yaml`

---

## Sprint 1: Core Backend & Data Infrastructure
**Duration:** Weeks 1–2 | **Total Points:** 24 SP  
**Primary Assignee:** Backend Developer | **Reviewer:** Tech Lead Architect / Sentinel  
**Objective:** Establish the high-performance fail-fast gateway, database migrations, atomic allocation CTE, and public holiday caching.

### Ticket Backlog
| ID | Title | SP | Dependencies | Acceptance Criteria Summary |
| :--- | :--- | :---: | :--- | :--- |
| `CPMS-S1-01` | Scaffold FastAPI gateway skeleton | 3 | None | Baseline FastAPI app, structured logging, health probe at `/api/v1/system/status`. |
| `CPMS-S1-02` | Implement LTA MOD-19 plate checksum | 2 | `CPMS-S1-01` | Pure Python validator matching Singapore LTA checksum algorithm; execution time < 1ms; comprehensive unit test suite for prefix rules and checksum letters. |
| `CPMS-S1-03` | Implement operating window gate middleware | 2 | `CPMS-S1-01` | Enforces 12:00–15:00 UTC+8 weekdays only; rejects off-hours with HTTP 422 `OUTSIDE_OPERATING_WINDOW` before any AI invocation. |
| `CPMS-S1-04` | Singapore Public Holiday sync & Redis cache | 3 | `CPMS-S1-01` | Daily sync worker against data.gov.sg API; fallback to local hardcoded holiday list on network failure; 24h cache TTL in Redis. |
| `CPMS-S1-05` | PostgreSQL schema migrations | 3 | None | DDL migrations for `voucher_pool` (with partial index `idx_voucher_pool_fifo_available`) and `redemption_logs` (with unique index `uq_redemption_vehicle_daily`). |
| `CPMS-S1-06` | Atomic allocation CTE repository | 5 | `CPMS-S1-05` | Single-statement CTE locking FIFO available voucher, updating status to `ISSUED`, and writing redemption log. Validated at 100 concurrent requests; zero orphaned vouchers on daily constraint collision. |
| `CPMS-S1-07` | Daily plate Bloom filter in Redis | 2 | `CPMS-S1-04` | High-speed edge check to reject vehicles that have already redeemed today before executing SQL or AI calls; auto-resets at 00:00 SGT. |
| `CPMS-S1-08` | HMAC-SHA256 peppered hashing module | 2 | `CPMS-S1-05` | Cryptographic hashing for plates and receipts (`HMAC-SHA256(SECRET_PEPPER, input)`); zero plaintext plate storage; unit tests for salt/pepper isolation. |
| `CPMS-S1-09` | OpenAPI contract conformance tests | 2 | `CPMS-S1-01` | Automated pytest suite validating gateway responses against `docs/openapi.yaml`. |

---

## Sprint 2: Multimodal AI Agent & Pipeline
**Duration:** Weeks 3–4 | **Total Points:** 30 SP  
**Primary Assignees:** Backend Developer, Tech Lead Architect  
**Objective:** Productionize multimodal receipt OCR with Google Gemini 2.0 Flash, zero-disk image streaming, local vLLM disaster recovery, and tenant fuzzy matching.

### Ticket Backlog
| ID | Title | SP | Dependencies | Acceptance Criteria Summary |
| :--- | :--- | :---: | :--- | :--- |
| `CPMS-S2-01` | Gemini 2.0 Flash SDK structured extraction | 5 | `CPMS-S1-01` | Integration via Vertex AI / Gemini API in `asia-southeast1`; Pydantic schema enforcement; returns structured `decision`, `confidence_score`, `extracted_data`, and `fraud_signals`. p95 latency < 1.8s. |
| `CPMS-S2-02` | Local vLLM Qwen2.5-VL container setup | 5 | `CPMS-S1-01` | Docker Compose stack on `syafiq-svr` (RTX 4090 24GB); AWQ quantized weights; standardized FastAPI adapter exposing identical JSON response format. |
| `CPMS-S2-03` | Resilient AI Circuit Breaker middleware | 3 | `CPMS-S2-01`, `CPMS-S2-02` | Monitors Gemini API; 3 consecutive timeouts (> 4.0s) or 5xx errors automatically divert traffic to local vLLM fallback with queue throttling. |
| `CPMS-S2-04` | Tenant registry seed & Redis fuzzy index | 3 | `CPMS-S1-04` | Pre-load 50 top mall merchants; Trigram / Levenshtein similarity index; minimum similarity threshold ≥ 0.85 for auto-approval. |
| `CPMS-S2-05` | Receipt business rule evaluation engine | 3 | `CPMS-S2-04` | Verifies eligible spend ≥ $30.00 SGD; deducts excluded items (lottery, gift vouchers); validates receipt timestamp within 12:00–15:00 window. |
| `CPMS-S2-06` | Fraud triage router | 3 | `CPMS-S2-01` | Routes receipts: confidence ≥ 0.90 & clean fraud flags → auto-approve; confidence 0.70–0.89 or fraud flags (screen glare, folded, altered) → manual review; confidence < 0.70 → auto-reject. |
| `CPMS-S2-07` | Ephemeral image lifecycle manager | 3 | `CPMS-S1-08` | In-memory byte streaming for approved receipts; AES-256 encrypted MinIO storage for flagged receipts with strict 24-hour auto-purge lifecycle rule. |
| `CPMS-S2-08` | End-to-end integration & load test suite | 5 | All Sprint 2 | Automated test suite verifying 100 concurrent redemption requests across happy paths, duplicate collisions, and edge cases EC-01 through EC-16. |

---

## Sprint 3: Mobile Frontend & Staff Dashboard
**Duration:** Week 5 | **Total Points:** 16 SP  
**Primary Assignees:** Frontend Developer, UI/UX designer, Iqbal  
**Objective:** Build high-converting, accessible mobile shopper portal and real-time customer service staff triage interface.

### Ticket Backlog
| ID | Title | SP | Dependencies | Acceptance Criteria Summary |
| :--- | :--- | :---: | :--- | :--- |
| `CPMS-S3-01` | Mobile submission interface | 3 | `CPMS-S1-01` | Mobile-first web UI; native camera capture (`capture="environment"`); reactive plate input with real-time MOD-19 validation feedback. |
| `CPMS-S3-02` | Code 128 SVG barcode renderer | 2 | `CPMS-S3-01` | JsBarcode integration rendering sharp SVG Code 128; directional insertion arrow pointing upward; dynamic prompt: "Set screen brightness to 100%". |
| `CPMS-S3-03` | Submission state machine UI | 3 | `CPMS-S3-01` | Polished reactive states: idle, camera capture, scanning, verifying, success (barcode), review queue wait, and actionable rejection feedback. |
| `CPMS-S3-04` | Staff Review Dashboard | 5 | `CPMS-S1-06`, `CPMS-S2-06` | Real-time WebSocket queue for flagged submissions; side-by-side receipt image & OCR diff; one-click Approve / Reject; 45s SLA countdown. |
| `CPMS-S3-05` | Admin audit & compliance portal | 3 | `CPMS-S3-04` | Manager PIN authentication; audit log viewer for all manual approvals; PDPA 72-hour manual purge trigger; voucher pool status monitor. |

---

## Sprint 4: Field Testing & Production Launch
**Duration:** Week 6 | **Total Points:** 11 SP  
**Primary Assignees:** QA Sentinel, DevOps Engineer, Delivery Coordinator  
**Objective:** Hardware compatibility testing on car park exit gantries, parallel shadow pilot, and production cutover.

### Ticket Backlog
| ID | Title | SP | Dependencies | Acceptance Criteria Summary |
| :--- | :--- | :---: | :--- | :--- |
| `CPMS-S4-01` | Gantry optical scanner compatibility tests | 3 | `CPMS-S3-02` | Physical field testing across 5 smartphone screen types (OLED, LCD, privacy glass, cracked screens); 100% scan success rate verified at exit gantries. |
| `CPMS-S4-02` | 1-week parallel mall pilot | 3 | All prior tickets | Dual-run parallel with Customer Service desk; staff shadow mode; verification of manual override rate < 5%. |
| `CPMS-S4-03` | Automated KPI reporting pipeline | 2 | `CPMS-S4-02` | Dashboards for p95 latency, approval accuracy, fraud catch rate, and daily redemption volume. |
| `CPMS-S4-04` | Production cutover & operational runbook | 2 | `CPMS-S4-02` | Health check automation, rollback scripts, automated pool exhaustion alerts via ntfy, on-call procedure. |
| `CPMS-S4-05` | Post-pilot user survey & retrospective | 1 | `CPMS-S4-02` | Analysis of shopper CSAT; sprint retrospective and Phase 2 enhancement backlog. |
