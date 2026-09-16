# CPMS Parking Redemption Engine: Technical Architecture & System Design

**Document ID:** ARCH-001  
**Version:** 1.0.0  
**Author:** Tech Lead Architect (`d8fdcb32-fc40-4970-81dc-a17d86334a8d`)  
**Status:** Approved for Sprint Planning  

---

## 1. Architectural Review & Gap Analysis

The initial project proposal (Section 5) specified a parallel processing pattern where the API Gateway dispatches incoming requests simultaneously to the Middleware, AI Agent Brain, and Holiday Cache:

```
[Initial Proposal Flow - Anti-Pattern]
CustomerMobile -> FastAPI -> [ Middleware (Parallel) | AI Agent Brain (Parallel) | Holiday Cache (Parallel) ]
```

### Critical Architectural Flaws Identified:
1. **Unconstrained LLM Resource Consumption:** Executing the AI Agent Brain in parallel with weekday, holiday, and operating hour checks wastes API budget and GPU cycles on submissions that are fundamentally ineligible (e.g., weekend submissions, out-of-window receipts, invalid license plates).
2. **Missing Input Checksum Pre-Filter:** Singapore vehicle license plates follow an algorithmic checksum (LTA MOD-19 algorithm). Validating this at the edge avoids processing bogus plate strings.
3. **Weak Salt/Pepper Strategy:** Simple SHA-256 on vehicle plates is susceptible to offline rainbow table precomputation (the active Singapore passenger car plate space is $< 1\text{M}$ active combinations).
4. **Voucher Pool Starvation & Lock Overhead:** Using `ORDER BY RANDOM()` causes a sequential table scan and memory sort under concurrency, degrading PostgreSQL throughput during the 12:00–15:00 lunch peak.

### Hardened Architecture Principles:
- **Strictly Sequential Fail-Fast Gateway:** Zero AI or database costs incurred if operating hours, public holidays, or plate formats fail validation.
- **HMAC-SHA256 with Secret Vault Pepper:** Vehicle plates and receipt keys are salted with an environment-injected secret pepper.
- **In-Memory Zero-Disk Image Lifecycle:** Non-flagged images are never written to disk; they exist only in memory buffers during the request lifecycle.
- **O(1) Lock-Free Voucher Allocation:** Deterministic FIFO selection backed by a partial index `WHERE status = 'AVAILABLE'` using `FOR UPDATE SKIP LOCKED`.

---

## 2. Component Topology

```mermaid
flowchart TD
    subgraph ClientLayer ["Client & Edge Layer"]
        User["Shopper Mobile Browser"]
        Gantry["Car Park Exit Gantry Scanner"]
    end

    subgraph GatewayLayer ["FastAPI Gateway & Edge Validation"]
        CF["Cloudflare / Reverse Proxy (TLS 1.3, Rate Limit)"]
        GateMiddleware["Pre-Flight Validation Middleware"]
        PlateValidator["SG Plate Checksum Validator (MOD-19)"]
        HolidayCheck["Operating Hours & Holiday Gate"]
    end

    subgraph CacheStore ["Redis In-Memory State (Docker)"]
        HolidayCache["Singapore Public Holiday Cache"]
        TenantCache["Tenant Registry & Fuzzy Index"]
        BloomPlate["Daily Vehicle Plate Bloom Filter"]
        SessionStore["Rate-Limit & Session Keys"]
    end

    subgraph InferenceEngine ["Multimodal AI Vision Service"]
        CircuitBreaker["Resilient Circuit Breaker"]
        GeminiPrimary["Primary: Google Gemini 2.0 Flash"]
        vLLMFallback["Fallback: Local Qwen2.5-VL (RTX 4090)"]
    end

    subgraph Persistence ["PostgreSQL 16 Storage (Docker)"]
        VoucherPool[("voucher_pool\n(Partial Index FIFO)")]
        RedemptionLogs[("redemption_logs\n(Audit & Deduplication)")]
        StaffAudit[("staff_audit_logs")]
    end

    subgraph AdminLayer ["Staff Operations"]
        StaffPortal["Staff Review Dashboard (Appsmith / React)"]
    end

    %% Flow connections
    User -->|1. Submit Photo + Plate| CF
    CF --> GateMiddleware
    GateMiddleware --> PlateValidator
    GateMiddleware --> HolidayCheck
    HolidayCheck <--> HolidayCache
    GateMiddleware <--> BloomPlate

    GateMiddleware -->|2. Validated Payload| CircuitBreaker
    CircuitBreaker -->|Primary REST| GeminiPrimary
    CircuitBreaker -.->|Failover gRPC| vLLMFallback

    GeminiPrimary -->|3. Structured JSON| GateMiddleware
    GateMiddleware <--> TenantCache

    GateMiddleware -->|4. Atomic Allocation CTE| Persistence
    VoucherPool --- RedemptionLogs

    GateMiddleware -->|5. Barcode Payload + Token| User
    User -->|6. Render Code 128 SVG| Gantry

    GateMiddleware -.->|Low Conf / Fraud Flag| StaffPortal
    StaffPortal -->|Manual Approval| Persistence
```

---

## 3. End-to-End Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Shopper as Shopper Mobile
    participant Gateway as FastAPI Gateway
    participant Redis as Redis Cache
    participant Vision as Gemini 2.0 Flash
    participant DB as PostgreSQL 16
    actor Staff as Staff Dashboard
    participant Gantry as CPMS Gantry

    Shopper->>Gateway: POST /api/v1/redemptions (Photo, Plate, Timestamp)
    
    rect rgb(240, 245, 255)
    note right of Gateway: Stage 1: Edge Validation (<10ms)
    Gateway->>Gateway: Verify SG Plate Checksum (MOD-19)
    Gateway->>Redis: Check Holiday & Operating Hours (12:00-15:00 UTC+8)
    Redis-->>Gateway: Status: Operational
    Gateway->>Redis: Check Plate Daily Bloom Filter (vehicle_hash)
    Redis-->>Gateway: Not yet redeemed today
    end

    rect rgb(255, 250, 240)
    note right of Gateway: Stage 2: Multimodal AI Inference (~1.5s)
    Gateway->>Vision: Process Receipt Image (Structured JSON Schema)
    Vision-->>Gateway: Return Extraction (Merchant, Total, Date, Time, Conf, Fraud)
    end

    rect rgb(240, 255, 240)
    note right of Gateway: Stage 3: Business Rules Verification (<15ms)
    Gateway->>Redis: Fuzzy match merchant against Tenant Registry (threshold >= 0.85)
    Redis-->>Gateway: Matched (e.g., "Toast Box")
    Gateway->>Gateway: Validate spend ($34.50 >= $30.00) & timestamp window
    end

    alt Confidence >= 0.90 AND Fraud Signals Clean (Auto-Approve)
        rect rgb(235, 255, 235)
        Gateway->>DB: Execute Atomic CTE (Insert Log + Claim Voucher FIFO)
        DB-->>Gateway: Allocated Voucher Code (e.g., "CPMS-88391204")
        Gateway->>Redis: Mark Vehicle Plate in Daily Cache
        Gateway-->>Shopper: 200 OK (Voucher Code, Code 128 Spec, Expiry: +2h)
        Shopper->>Shopper: Render SVG Barcode (JsBarcode) at 100% Brightness
        Shopper->>Gantry: Scan Barcode at Exit Scanner
        Gantry-->>Shopper: Gate Opens (CPMS Barrier Lifted)
        end
    else Confidence between 0.70 and 0.89 OR Fraud Flag Triggered (Manual Review)
        rect rgb(255, 245, 235)
        Gateway->>DB: Store pending_review record (Encrypted Image Reference)
        Gateway->>Staff: Push to Staff Review Queue (WebSocket)
        Gateway-->>Shopper: 202 Accepted ("Receipt under quick review, please wait")
        Staff->>Staff: Staff reviews image & clicks "Approve"
        Staff->>DB: Trigger Atomic Voucher Claim
        DB-->>Staff: Voucher Allocated
        Staff-->>Shopper: Push Voucher to Client (WebSocket / Poll)
        end
    else Confidence < 0.70 OR Rule Violation (Rejection)
        Gateway-->>Shopper: 422 Unprocessable Entity ("Receipt ineligible: Spend below $30 SGD")
    end
```

---

## 4. Singapore Vehicle Plate Checksum Algorithm (MOD-19)

To ensure zero invalid plate allocations, the gateway executes the Land Transport Authority (LTA) algorithm before processing:
1. Prefix conversion: Single letter has fixed numerical mapping; 2 letters use 2 digits; 3 letters discard first letter (e.g., `SBA` $\rightarrow$ `BA`).
2. Numerical extraction: Digits padded to 4 numbers with leading zeros (e.g., `123` $\rightarrow$ `0123`).
3. Weight multiplication: Weights $[9, 4, 5, 4, 3, 2]$ applied to components.
4. Modulo 19 remainder mapped to checksum letter array `['A','Z','Y','X','U','T','S','R','P','M','L','K','J','H','G','E','D','C','B']`.

Any mismatch rejects the submission in $<1\text{ms}$ with zero downstream overhead.

---

## 5. Anti-Fraud & Data Protection Architecture

### Peppered Hash Storage
Vehicle plates are never stored in plaintext:
$$\text{vehicle\_plate\_hash} = \text{HMAC-SHA256}(K_{\text{secret\_pepper}}, \text{plate\_normalized})$$
Receipt keys are strictly unique across tenant, receipt number, and transaction date:
$$\text{receipt\_hash} = \text{HMAC-SHA256}(K_{\text{secret\_pepper}}, \text{tenant\_normalized} \mathbin{\Vert} \text{receipt\_no} \mathbin{\Vert} \text{date})$$

### Ephemeral Storage Policy
- **Auto-Approved:** Receipt image buffer discarded from memory immediately after API response dispatch. Zero image bytes stored.
- **Manual Review:** Temporarily encrypted with AES-256 and uploaded to an S3/MinIO bucket with bucket lifecycle policy set to hard delete after 24 hours.
- **72h Data Pruning:** Cron job deletes all logs older than 72h, retaining only aggregated merchant redemption counts.
