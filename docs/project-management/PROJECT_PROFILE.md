# Project Profile: Autonomous Receipt-to-Barcode Parking Redemption System

**Initiative Key:** `CPMS-REDEMPTION`  
**Multica Project ID:** `94727900-d3dd-4160-8080-9b12afef8ed5`  
**Icon:** 🅿️  
**Priority:** High  
**Status:** 🟢 `in_progress`  
**Project Lead:** Project Manager & Delivery Coordinator (`a78acb91-1feb-4cbe-ac8d-71af0f63edbf`)  
**Timeline:** 2026-09-16 → 2026-11-13 (6 Weeks, 4 Execution Sprints)  
**Primary Repository:** `https://github.com/syafiqabdha/cpms-redemption.git`  

---

## 1. Executive Summary & Objective

The **Autonomous Receipt-to-Barcode Parking Redemption System (CPMS)** automates and replaces physical customer service desk parking validation operations at retail shopping malls.

Shoppers upload physical thermal receipts via a mobile web portal to claim complimentary parking. The system executes a rigorous sequential pre-flight fail-fast filter (LTA MOD-19 plate validator, 12:00–15:00 operating window, holiday exclusions, Redis Bloom filter) before triggering multimodal AI vision extraction (Google Gemini 2.0 Flash in `asia-southeast1`). Upon approval, a single-statement atomic allocation CTE reserves a voucher and issues an SVG Code 128 barcode directly scannable at car park exit gantries.

### Key Value Metrics
- **Queue Elimination:** Replaces physical queues at customer service desks with a sub-30 second self-service digital flow.
- **Cost Reduction:** Reduces mall customer service desk staffing requirements during peak 12:00–15:00 weekday redemption surges.
- **Fraud Prevention:** Algorithmic detection of folded receipts, re-scans, digital screen captures, non-tenant receipts, and multi-vehicle claims.
- **Zero Plaintext PII:** Strict compliance with Singapore PDPA standards via HMAC-SHA256 peppered hashing.

---

## 2. Key Performance Indicators (KPIs) & Target Gates

| Metric | Target | Measurement Method | Current Status |
| :--- | :---: | :--- | :---: |
| **Approval Accuracy** | ≥ 95% | Manual review override rate < 5% | Planned (Pilot Phase) |
| **Processing Latency (p95)** | < 30s | Photo upload to barcode render latency | On Track (< 1.8s AI target) |
| **System Availability** | ≥ 99.5% | Gateway & allocation pipeline uptime | 🟢 On Track |
| **Edge Fraud Catch Rate** | ≥ 90% | Tampered, folded, or duplicate receipts blocked | In Progress |
| **Shopper CSAT** | ≥ 4.5 / 5.0 | Post-redemption exit survey score | Planned (Sprint 4) |

---

## 3. Architecture & Technical Stack

```
[Shopper Mobile Browser] 
          │  (HTTPS / Camera Capture)
          ▼
[FastAPI Gateway Engine] ──(Fail-Fast Filters)──► [LTA MOD-19 Checksum (<1ms)]
          │                                      ► [Time Window Gate (12:00-15:00)]
          │                                      ► [Redis Holiday & Bloom Edge Filter]
          ▼
[AI Vision Extraction Router]
     ├── Primary: Google Gemini 2.0 Flash (asia-southeast1, p95 < 1.8s)
     └── Fallback: Local vLLM Qwen2.5-VL AWQ (RTX 4090 on syafiq-svr)
          │
          ▼
[PostgreSQL 16 Atomic Allocation CTE]
     ├── Lock-free FIFO Voucher Pool Reservation
     └── Idempotent Redemption Audit Log (HMAC-SHA256 Peppered Hash)
          │
          ▼
[Client-Side SVG Code 128 Barcode Render]
```

### Infrastructure & Technology Standards
- **Language / Framework:** Python 3.12, FastAPI, Pydantic v2, Uvicorn (ASGI)
- **Data Persistence:** PostgreSQL 16 (Partial FIFO indexes, strict foreign keys, unique constraint idempotency)
- **Cache & Edge Rejection:** Redis 7 (SG Public Holiday cache, daily vehicle Bloom filter, tenant fuzzy index)
- **Multimodal AI:** Google Gemini 2.0 Flash via Vertex AI/Gemini API; local fallback via vLLM (Qwen2.5-VL AWQ on RTX 4090)
- **Security & Privacy:** PDPA-compliant HMAC-SHA256 peppered hashing for vehicle plates and receipt hashes; ephemeral in-memory byte streaming (no raw image disk persistence for approved transactions)
- **Frontend / Client:** Mobile-optimized responsive web app, client-side SVG Code 128 barcode generator (JsBarcode), WebSockets for staff triage

---

## 4. Team & Squad Ownership Matrix

| Role | Assignee / Entity | Responsibilities |
| :--- | :--- | :--- |
| **Delivery Coordinator / PM** | Project Manager & Delivery Coordinator (`a78acb91-...`) | Roadmap tracking, milestone gating, ticket decomposition, sprint coordination |
| **Tech Lead / Architect** | Tech Lead Architect (`a45ef776-...`) | System architecture, concurrency design, ADR enforcement, code reviews |
| **Backend Engineering** | Backend Developer (`29e280c2-...`) | FastAPI gateway, LTA validator, holiday sync, PostgreSQL DDL & CTE, Redis Bloom filter |
| **Frontend Engineering** | Frontend Developer (`cf0602b2-...`) | Mobile web capture UI, barcode rendering, reactive state machine |
| **UI/UX Design** | UI/UX Designer / Iqbal | Submission wireframes, staff dashboard UX, gantry alignment guides |
| **QA & Verification** | QA Sentinel (`cf0602b2-...`) | Concurrency stress tests, OpenAPI conformance, edge cases EC-01–EC-16 |
| **DevOps & Infra** | DevOps & Infrastructure Engineer | Multi-stage Docker, Coolify deployment, local vLLM container orchestration |

---

## 5. Milestone & Sprint Breakdown (81 Total SP)

### Milestone 1: Phase 1 Planning & Architecture Gate (Status: 🟢 Done)
- **Completed:** 2026-09-16
- **Deliverables:** Architectural System Design, Concurrency & Voucher Pool Design, ADR-001 (Vision Extraction Engine), OpenAPI 3.1.0 Contract, Master Roadmap, Sprint Backlog.
- **Verification:** PR #1 merged into `master`.

### Milestone 2: Sprint 1 Core Backend & Data Infrastructure (Status: 🟢 In Progress — 24 SP)
- **Target Dates:** 2026-09-16 → 2026-10-02
- **Key Tickets:**
  - `PAN-48` (`CPMS-S1-01`): Scaffold FastAPI gateway skeleton + middleware pipeline (✅ **Done** — PR #2 merged)
  - `PAN-49` (`CPMS-S1-05`): PostgreSQL schema migration: `voucher_pool` & `redemption_logs` (🔄 **In Progress**)
  - `PAN-50` (`CPMS-S1-02`): Pure Python LTA MOD-19 license plate checksum validator (📋 Backlog)
  - `PAN-51` (`CPMS-S1-03`): Operating window gate middleware (12:00–15:00 UTC+8) (📋 Backlog)
  - `PAN-52` (`CPMS-S1-04`): Singapore Public Holiday sync & Redis cache (📋 Backlog)
  - `PAN-53` (`CPMS-S1-06`): Atomic allocation CTE repository & concurrency stress tests (📋 Backlog)
  - `PAN-54` (`CPMS-S1-07`): Daily vehicle plate Bloom filter in Redis (📋 Backlog)
  - `PAN-55` (`CPMS-S1-08`): Cryptographic HMAC-SHA256 peppered hashing module (📋 Backlog)
  - `PAN-56` (`CPMS-S1-09`): OpenAPI contract conformance automated test suite (📋 Backlog)

### Milestone 3: Sprint 2 Multimodal AI Agent & Pipeline (Status: 📋 Planned — 30 SP)
- **Target Dates:** 2026-10-05 → 2026-10-16
- **Scope:** Gemini 2.0 Flash structured JSON extraction, local vLLM Qwen2.5-VL container fallback, circuit breaker, tenant fuzzy matching, receipt business rule engine, fraud router, ephemeral image manager.

### Milestone 4: Sprint 3 Mobile Frontend & Staff Dashboard (Status: 📋 Planned — 16 SP)
- **Target Dates:** 2026-10-19 → 2026-10-30
- **Scope:** Mobile receipt capture UI, client-side SVG Code 128 barcode renderer, reactive state machine, real-time WebSocket staff review portal, manager audit & compliance UI.

### Milestone 5: Sprint 4 Field Testing & Production Launch (Status: 📋 Planned — 11 SP)
- **Target Dates:** 2026-11-02 → 2026-11-13
- **Scope:** 5-device car park gantry optical scanner verification, 1-week parallel customer service desk pilot, automated KPI dashboards, cutover & operational runbooks.

---

## 6. Live Velocity & Issue Execution Summary

```
Total Issues Tracked: 11
├── Done: 2 (18.2%)
│   ├── PAN-46: Phase 1 Planning & Architecture Gate (PR #1 merged)
│   └── PAN-48: CPMS-S1-01 FastAPI gateway skeleton (PR #2 merged)
├── In Progress: 2 (18.2%)
│   ├── PAN-47: Sprint 1 Core Backend & Data Infrastructure (Parent Epic)
│   └── PAN-49: CPMS-S1-05 PostgreSQL schema migrations (Active dev)
└── Backlog: 7 (63.6%)
    ├── PAN-50: CPMS-S1-02 LTA MOD-19 validator
    ├── PAN-51: CPMS-S1-03 Operating window gate
    ├── PAN-52: CPMS-S1-04 Singapore Public Holiday sync
    ├── PAN-53: CPMS-S1-06 Atomic allocation CTE
    ├── PAN-54: CPMS-S1-07 Redis daily plate Bloom filter
    ├── PAN-55: CPMS-S1-08 HMAC-SHA256 peppered hashing
    └── PAN-56: CPMS-S1-09 OpenAPI contract conformance tests
```

---

## 7. Critical Path Risks & Mitigations

| Risk Vector | Severity | Trigger | Mitigation |
| :--- | :---: | :--- | :--- |
| **Gantry Optical Scan Failure** | 🟡 Medium | Screen reflections or dim displays prevent exit barcode reading. | Force 100% brightness banner; directional alignment marker; test against OLED/LCD/privacy screen protectors in Sprint 4. |
| **AI Rate Limit / Latency Spike** | 🟢 Low | Cloud API spike during peak lunch hour (12:00–15:00). | Fail-fast edge filters reject invalid requests first; automated circuit breaker diverts to local RTX 4090 Qwen2.5-VL. |
| **Voucher Pool Depletion** | 🟢 Low | Pool drops below safety buffer during lunch traffic. | Daily automated replenishment cron; ntfy push alerts at 20% threshold; graceful HTTP 503 retry guidance. |
| **PDPA Data Leakage** | 🟢 Low | Plaintext storage of car license plates or receipt images. | Mandatory HMAC-SHA256 peppered hashing; ephemeral RAM streaming; strict 24h retention on flagged audit images. |
