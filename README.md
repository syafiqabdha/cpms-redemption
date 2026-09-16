---
aliases:
  - "Project Proposal: Autonomous Receipt-to-Barcode Parking Redemption System"
  - "Smart Parking Redemption Engine"
tags:
  - project/proposal
  - parking-redemption
  - ai-automation
status: proposal
priority: high
owner: Syafiq Abdullah
related:
  - "[[CPMS Integration Playbook]]"
  - "[[AI Vision Agent Framework]]"
  - "[[PDPA Compliance Checklist]]"
---

## 1. Executive Summary & Objective

| Field | Value |
| --- | --- |
| **Project Title** | Smart Parking Receipt-to-Barcode Autonomous Redemption Engine (CPMS) |
| **Objective** | Replace manual Customer Service desk operations with a fully automated, self-service mobile web portal powered by a Multimodal AI Agent |
| **Core Value** | Shoppers scan an in-mall QR code, capture a photo of their receipt, input their vehicle registration number, and receive an instantly generated **Code 128 barcode** on-screen to scan directly at car park exit gantries |
| **Status** | Proposal Stage |

> **Key Problem**: Manual redemption creates 20-min+ queues during lunch rush. This system eliminates the desk entirely — shopper self-serves in under 30s.

## 2. Assumptions & Constraints

1. **Deployment Target**: Singapore mall with existing CPMS (Car Park Management System) voucher integration
2. **Regulatory**: PDPA compliance mandatory — no unencrypted PII/image storage
3. **Hardware**: Exit gantries must support Code 128 barcode scanning (most do)
4. **Network**: 4G/5G coverage sufficient; offline fallback mode if gateway fails
5. **Throughput Target**: 100 concurrent redemptions, peak 500/day per kiosk

## 3. Business Rules & Qualification Criteria

| Parameter | Operational Rule | Enforcement Method |
| --- | --- | --- |
| **Valid Days** | Monday–Friday only (UTC+8) | Backend validation: `datetime.weekday() < 5` |
| **Public Holidays** | Excluded per Singapore calendar | Public Holidays API check |
| **Time Window** | 12:00 PM – 3:00 PM (receipt timestamp) | AI extracts timestamp; verify `$12:00 ≤ Time ≤ 15:00$` |
| **Minimum Spend** | ≥ $30.00 SGD per single receipt | Sum line items; verify threshold |
| **Tenant Scope** | Participating mall tenants only | Fuzzy match against tenant registry (threshold ≥ 0.85 similarity) |
| **Usage Limit** | 1 redemption per vehicle per calendar day | Unique database constraint on `(vehicle_plate, date)` |
| **Confidence Threshold** | ≥ 0.90 | Auto-approve; below → manual review |

## 4. Security & Privacy

### PDPA Compliance

- **Vehicle Plates**: Hash with SHA-256 + pepper (secret key) before storage; plaintext never persisted
- **Receipt Images**: Encrypted at rest for 24h max; auto-purge after processing
- **Data Retention**: All PII deleted within 72h of voucher expiry (2h from issuance)
- **Access Control**: Role-based (admin/staff); audit logs for all manual overrides
- **Encryption**: TLS 1.3 in transit; AES-256 at rest

### Fraud Detection Matrix

| Signal | Detection Method | Response |
| --- | --- | --- |
| Screen photo | ML model trained on screen glare patterns | Flag + require manual review |
| Image tampering | Font anomaly detection | Flag |
| Folded/obscured | Edge detection + contrast analysis | Flag |

## 5. System Architecture & Workflow

```
                    ┌──────────────────────┐
                    │  Customer Mobile     │
                    │  Browser (Web App)   │
                    └──────────┬───────────┘
                               │
       (1) QR scan + camera    │
       photo + vehicle plate   │
                               ▼
                    ┌──────────────────────┐
                    │   API Gateway        │
                    │   (FastAPI)          │
                    └──────────┬───────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Middleware      │ │ AI Agent Brain  │ │ Holiday Cache   │
│ - Weekday check │ │ (Vision LLM)    │ │ - Singapore     │
│ - Holiday check │ │ - OCR extraction│ │ - Updated daily │
│ - Time window   │ │ - Tenant match  │ │ - Fallback list │
└─────────────────┘ └─────────────────┘ └─────────────────┘
           │                   │
           │              ┌────┴────┐
           │              │         │
           │              ▼         ▼
           │      ┌─────────────┐ ┌─────────────┐
           │      │ PostgreSQL  │ │ Redis Cache │
           │      │ - voucher   │ │ - Session   │
           │      │ - redemption│ │ - Result    │
           │      │   pool      │ │   cache     │
           │      └─────────────┘ └─────────────┘
           │              │
           └──────────────┘
                               ▼
                    ┌──────────────────────┐
                    │ Mobile Response      │
                    │ - Code 128 SVG barcode│
                    │ - Voucher code       │
                    └──────────────────────┘
```

## 6. AI Agent Backend Brain Specification

### Decision Flow

1. **Extract** → OCR receipt, parse merchant, date, time, totals, line items
2. **Validate** → Check tenant, time, spend threshold
3. **Deduce** → Subtract excluded items (gift cards, lottery)
4. **Fraud Check** → Screen photo, tampering, fold detection
5. **Route** → APPROVE / REJECT / MANUAL REVIEW based on confidence

> **Fallback**: If printed total is faded or smudged, calculate sum from individual line items.

### Structured Output Schema (JSON)

```json
{
  "decision": "APPROVED",
  "confidence_score": 0.98,
  "rejection_reason": null,
  "extracted_data": {
    "merchant_raw": "TOAST BOX #01-12",
    "merchant_matched": "Toast Box",
    "is_participating_tenant": true,
    "receipt_number": "TB-20260916-0442",
    "transaction_date": "2026-09-16",
    "transaction_time": "12:45",
    "gross_total": 34.50,
    "excluded_amount": 0.00,
    "eligible_total": 34.50
  },
  "fraud_signals": {
    "is_screen_photo": false,
    "image_tampering_detected": false,
    "receipt_folded_or_obscured": false
  }
}
```

### Confidence Thresholds

| Range | Action |
| --- | --- |
| ≥ 0.90 | Auto-approve — issue voucher immediately |
| 0.70 – 0.89 | Manual review queue — staff one-click approval |
| < 0.70 | Auto-reject with actionable reason |

## 7. Database Schema & Concurrency Design

```sql
-- 1. CPMS Voucher Inventory Pool
CREATE TABLE voucher_pool (
    id SERIAL PRIMARY KEY,
    voucher_code VARCHAR(32) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'AVAILABLE',  -- AVAILABLE, ISSUED, REDEEMED, EXPIRED
    issued_to_vehicle VARCHAR(64),         -- SHA256 hash of plate
    issued_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE
);

-- 2. Audit & Redemption Log
CREATE TABLE redemption_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_plate_hash VARCHAR(64) NOT NULL,  -- SHA256 hash
    merchant_name VARCHAR(100) NOT NULL,
    receipt_hash VARCHAR(64) UNIQUE NOT NULL,  -- SHA256(tenant + receipt_no + date)
    receipt_amount NUMERIC(10, 2) NOT NULL,
    receipt_timestamp TIMESTAMP NOT NULL,
    voucher_code_issued VARCHAR(32) REFERENCES voucher_pool(voucher_code),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Unique constraint for 1-per-car-per-day
CREATE UNIQUE INDEX unique_daily_redemption 
ON redemption_logs (vehicle_plate_hash, DATE(receipt_timestamp));
```

### Atomic Allocation Query

```sql
UPDATE voucher_pool
SET status = 'ISSUED',
    issued_to_vehicle = :vehicle_hash,
    issued_at = NOW(),
    expires_at = NOW() + INTERVAL '2 hours'
WHERE id = (
    SELECT id FROM voucher_pool
    WHERE status = 'AVAILABLE'
    ORDER BY RANDOM()  -- Fair distribution
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
RETURNING voucher_code;
```

## 8. Frontend & Barcode Engine Specification

### Mobile UI Components

```html
<!-- Camera capture -->
<input type="file" accept="image/*" capture="environment" id="receipt-input">

<!-- Barcode display -->
<div class="barcode-card" style="background: #FFFFFF; padding: 24px; text-align: center; border-radius: 8px;">
  <!-- Directional Insertion Triangle -->
  <div style="width: 0; height: 0; border-left: 28px solid transparent; border-right: 28px solid transparent; border-bottom: 24px solid #000000; margin: 0 auto 16px;"></div>
  
  <!-- Code 128 SVG Container -->
  <svg id="barcode-canvas"></svg>
  
  <p style="font-family: monospace; font-size: 13px; color: #333; margin-top: 10px;">
    Scan at exit gantry • Set screen brightness to 100%
  </p>
</div>

<script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
<script>
JsBarcode("#barcode-canvas", "0001051165", {
  format: "CODE128",
  width: 2.4,
  height: 85,
  displayValue: true,
  font: "monospace",
  fontSize: 16,
  textMargin: 6
});
</script>
```

> **Gantry Scanning Tip**: Screen must be at 100% brightness. SVG renders sharp at any zoom. Directional triangle must point into the scan beam.

## 9. Error Handling & Edge Cases

| Scenario | Response | Owner |
| --- | --- | --- |
| Vision API timeout | "System busy, try again in 30s" | Automated retry (3x, 5s backoff) |
| Database unavailable | Maintenance page + queue position | Ops team |
| Low confidence result | Manual review queue | Staff (1-click approve/reject) |
| Invalid image format | "Please retake photo" | User |
| Voucher pool exhausted | Show queue position + ETA | Auto-replenish nightly |
| PDPA override needed | Require manager PIN + log audit trail | Admin |

## 10. Technology Stack Evaluation

| Layer | Managed Option | Self-Hosted Option |
| --- | --- | --- |
| **Vision AI** | Google Gemini 2.0 Flash | Qwen2-VL via vLLM on RTX 4090 |
| **Backend API** | Railway / Render | FastAPI on Coolify (Ubuntu Server) |
| **Database** | Supabase Cloud | PostgreSQL 16 on Docker |
| **Frontend** | Cloudflare Pages | Nginx static container |
| **Admin Dashboard** | Appsmith Cloud | Self-hosted Appsmith |
| **Cache** | — | Redis on Docker |

## 11. Implementation Roadmap

```
Week 1-2:      Week 3-4:          Week 5:           Week 6:
┌─────────────┐ ┌────────────────┐ ┌─────────────┐ ┌────────────────┐
│ Backend     │ │ AI Agent       │ │ Frontend    │ │ Field Test     │
│ & Data      │ │ Integration    │ │ & Admin UI  │ │ & Go-Live      │
│ • DB schema │ │ • Vision API   │ │ • Mobile UI │ │ • Gantry scan  │
│ • Holiday   │ │ • Tenant match │ │ • Barcode   │ │ • 1-week pilot │
│ • Voucher   │ │ • Fraud rules  │ │ • Staff     │ │ • Full launch  │
│   pool      │ │                │ │   dashboard │ │                │
└─────────────┘ └────────────────┘ ┌─────────────┐ └────────────────┘
                                    │ Success     │
                                    │ metrics     │
                                    │ reporting   │
                                    └─────────────┘
```

### Sprint 1: Core Backend & Data Infrastructure

- PostgreSQL database with atomic locking mechanisms
- Pre-authorize CPMS voucher code pools (daily batches via cron)
- Singapore Public Holiday sync + weekday/time middleware filters

### Sprint 2: Multimodal AI Agent Development

- Vision API integration with structured extraction schemas
- Tenant registry (50 top mall merchants) + fuzzy matching
- Duplicate receipt hash + screen-detection anti-fraud

### Sprint 3: Frontend & Admin Triage Dashboard

- Responsive mobile submission interface with live camera capture
- Client-side SVG Code 128 rendering + directional indicator
- Staff fallback dashboard for low-confidence approvals

### Sprint 4: Hardware Field Testing & Production Launch

- Validate mobile-screen scanning on exit gantry optical scanners
- 1-week pilot parallel with traditional desk operations
- Full cutover to autonomous self-service

## 12. Success Metrics

| Metric | Target | Measurement |
| --- | --- | --- |
| **Approval Accuracy** | ≥ 95% | Manual review override rate |
| **Processing Time** | < 30s | p95 from photo to barcode |
| **System Uptime** | ≥ 99.5% | Monthly downtime |
| **Fraud Detection** | ≥ 90% | Flagged receipts that fail validation |
| **User Satisfaction** | ≥ 4.5/5 | Post-pilot survey |

## 13. Risk Register

| Risk | Probability | Impact | Mitigation |
| --- | --- | --- | --- |
| **PDPA violation** | Low | Critical | Encrypt PII; auto-delete; audit logs |
| **Vision API cost overrun** | Medium | High | Set usage budget; local fallback ready |
| **Voucher pool exhaustion** | Low | High | Daily batch replenishment; alert on <20% |
| **Gantry scan failure** | Medium | Medium | Pre-launch compatibility testing across 5 device types |
| **AI drift / degraded accuracy** | Low | Medium | Weekly accuracy audit; A/B testing pipeline |

---

*Updated: 2026-09-16*
*Author: [[Syafiq Abdullah]]*

## Linked Notes

- [[CPMS Integration Playbook]] — API contract details, voucher format spec
- [[AI Vision Agent Framework]] — prompt templates, confidence calibration
- [[PDPA Compliance Checklist]] — audit trail requirements, data deletion procedures
- [[Coolify Deployment Guide]] — self-hosted stack deployment steps
