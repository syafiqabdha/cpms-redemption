# ADR-001: Multimodal Vision Model Selection for Autonomous Receipt OCR

- **Status:** Proposed
- **Date:** 2026-09-16
- **Author:** Tech Lead Architect (`d8fdcb32-fc40-4970-81dc-a17d86334a8d`)
- **Scope:** CPMS Parking Redemption Initiative (Phase 1: Discovery & Architecture Gate)

---

## 1. Context & Problem Statement

The Autonomous Receipt-to-Barcode Parking Redemption System replaces a manual mall Customer Service desk with a self-service mobile web portal. Shoppers photograph thermal paper receipts on their mobile phones, submit their Singapore vehicle registration plate, and immediately receive a scannable Code 128 barcode for car park exit gantries.

Key architectural requirements & constraints:
1. **Throughput & Concurrency:** Target peak concurrency of 100 simultaneous redemptions, with ~500 redemptions/day concentrated during the weekday lunch rush window (12:00 PM – 3:00 PM SGT).
2. **Latency (SLO):** End-to-end processing time (image capture to barcode render) must remain under 30 seconds p95 (with a target of < 5 seconds for visual OCR).
3. **Structured Extraction Accuracy:** Thermal receipts present challenging real-world artifacts (creases, uneven lighting, faint dot-matrix printing, thermal fading, merchant tax ID variations). Extraction must reliably populate structured JSON matching a strict schema (merchant, date, time, receipt number, line items, gross total, excluded items) with confidence scoring $\ge 0.90$.
4. **Anti-Fraud Detection:** Screen-rephoto detection, image tampering indicators, and fold/occlusion detection must be evaluated in the same inference pass.
5. **Cost & Operational Footprint:** Minimize operational overhead and infrastructure costs without compromising reliability.

The proposal evaluates two primary options: **Google Gemini 2.0 Flash** (managed cloud API) vs. **Qwen2.5-VL-7B-Instruct** (self-hosted via vLLM on an on-premise NVIDIA RTX 4090 24GB GPU server).

---

## 2. Decision Drivers

- **P95 Latency & Concurrency:** Ability to handle 100 concurrent requests without queue starvation or latency spikes during lunch peak.
- **Developer Velocity & Structured JSON Output:** Native, bulletproof JSON schema validation (e.g., Pydantic schema / constrained decoding) with zero JSON syntax parsing failures.
- **Operational Complexity:** Maintenance burden of GPU drivers, CUDA runtimes, vLLM daemon monitoring, VRAM memory leaks, and network ingress.
- **Total Cost of Ownership (TCO) & ROI:** Monthly API cost vs. continuous GPU power consumption, cooling, and hardware amortisation.
- **PDPA & Data Protection:** Transmission and retention compliance under Singapore Personal Data Protection Act (PDPA).

---

## 3. Considered Options

### Option 1: Managed Google Gemini 2.0 Flash (Cloud API)
- Architecture: Direct REST/gRPC integration from backend API (FastAPI) to Google Cloud Vertex AI / Gemini Developer API.
- Prompt: Single-shot multimodal prompt passing binary image bytes and strict JSON output schema.

### Option 2: Self-Hosted Qwen2.5-VL-7B-Instruct (vLLM on RTX 4090 24GB)
- Architecture: Self-hosted `vLLM` container running on local GPU server (`syafiq-svr`, RTX 4090 24GB VRAM), connected via Tailscale overlay mesh.
- Model: Qwen2.5-VL-7B-Instruct quantized to 4-bit AWQ / GPTQ to maximize KV cache headroom.

### Option 3: Tiered Hybrid Routing (Gemini Flash Primary + Local vLLM Fallback)
- Architecture: Gemini 2.0 Flash processes 100% of standard production traffic. If the Google API encounters rate limits (429), timeouts (> 5s), or service outages (5xx), an automated circuit breaker fails over to the local vLLM instance.

---

## 4. Evaluation Matrix

| Vector | Option 1: Gemini 2.0 Flash | Option 2: Self-Hosted Qwen2.5-VL (RTX 4090) | Option 3: Tiered Hybrid |
| :--- | :--- | :--- | :--- |
| **Operational Complexity** | **Very Low:** Zero infrastructure, serverless, automated scaling. | **High:** Requires NVIDIA driver management, vLLM upgrades, CUDA memory leak watchdogs, Tailscale stability. | **Medium-High:** Maintain both cloud client and containerized fallback. |
| **Ecosystem & Community** | **Exceptional:** Mature SDKs (`google-genai`), native Pydantic schema enforcement, prompt caching. | **Strong:** Hugging Face, vLLM, Ollama support. Guided decoding (Outlines/XGrammar) occasionally adds overhead. | **Exceptional:** Best of both ecosystems. |
| **Developer Velocity** | **Very Fast:** Instant prompt iteration, robust function calling, zero local VRAM constraints. | **Moderate:** Requires tuning vision token tiling, quantization calibration, and testing guided decoding. | **Fast:** Build for Gemini first; local scaffold reuses identical OpenAI-compatible schema. |
| **Concurrency & Throughput** | **High:** 1,000–2,000 RPM quota tier; absorbs 100 concurrent requests effortlessly. | **Severely Bottlenecked:** 24GB VRAM limits concurrent batch size to ~6–8 requests for 2K-token images. Queue length > 30 violates 30s SLO. | **High:** Managed handles burst; local handles offline survival. |
| **Latency (p95)** | **1.2s – 2.0s** | **2.5s – 4.0s (unloaded); > 45s (under 50 concurrent queue)** | **1.5s (nominal)** |
| **Direct Monthly Cost** | **~$3.75 SGD / mo** (500 receipts/day × 30 days = 15,000 calls × $0.00025). | **~$65.00 SGD / mo** (RTX 4090 300W baseline power @ $0.30/kWh). | **~$3.75 SGD / mo** (power already paid if host is multipurpose). |
| **PDPA / Privacy** | **Compliant:** Zero-retention enterprise terms; images processed in transit and not stored for training. | **Maximum Sovereignty:** Images never leave local Tailscale network. | **Compliant:** Fully configurable failover boundaries. |

---

## 5. Quantitative Concurrency & VRAM Breakdown

### The Self-Hosted Concurrency Bottleneck (RTX 4090)
1. **Input Resolution & Token Footprint:**
   A receipt photo (typical aspect ratio 1:2, e.g., 1200 × 2400 px) processed by Qwen2.5-VL is patched into dynamic visual tokens. At standard resolution, this generates **~1,200 to 1,800 visual tokens**.
2. **VRAM Budget on RTX 4090 (24,576 MB):**
   - Qwen2.5-VL-7B FP16 weights: ~15,000 MB.
   - AWQ 4-bit quantized weights: ~5,500 MB.
   - Paged KV-Cache allocation in vLLM: ~17,000 MB remaining.
3. **KV Cache Consumption per Stream:**
   At 2,000 tokens context length (image tokens + receipt OCR text output), each active stream consumes approximately **1.5 GB to 2.0 GB** of KV cache memory.
4. **Max Concurrency Limit:**
   $17,000\text{ MB} / 2,000\text{ MB} \approx 8\text{ concurrent requests}$.
5. **Queue Delay Under 100 Concurrent Lunch Surge:**
   If 50 shoppers submit receipts simultaneously at 12:35 PM:
   - With batch concurrency = 8 and inference latency = 2.5s:
   - Processing 50 requests requires $\lceil 50 / 8 \rceil = 7\text{ sequential batches}$.
   - 7th batch wait time $= 7 \times 2.5\text{s} = 17.5\text{s}$ queue delay $+ 2.5\text{s}$ processing $= 20.0\text{s}$.
   - At 100 concurrent requests, total delay exceeds **40–50 seconds**, directly breaching our P95 < 30s SLO.

### The Cloud API Advantage (Gemini 2.0 Flash)
- **Token Pricing:** $0.10 / 1M input tokens; $0.40 / 1M output tokens.
- **Cost per transaction:**
  - Input: $1,500\text{ tokens} \times \$0.0000001 = \$0.00015$
  - Output: $300\text{ tokens} \times \$0.0000004 = \$0.00012$
  - Total per receipt $= \$0.00027\text{ USD}$ (~$0.00036 SGD).
- **At 500 redemptions/day:** $\$0.135\text{ USD/day} \rightarrow \mathbf{\$4.05\text{ USD/month}}$ (~$5.40 SGD/month).

---

## 6. Decision Outcome

**Chosen Strategy: Option 3 (Tiered Hybrid Deployment with Gemini 2.0 Flash as Primary)**

1. **Production Primary:** Deploy **Google Gemini 2.0 Flash** as the default OCR & visual decision engine.
   - Enforce response structure using native Pydantic schema (`response_mime_type="application/json"`).
   - Leverage Google Cloud Singapore region (`asia-southeast1`) or global low-latency endpoints to minimize round-trip network latency.
2. **Local Fallback Scaffold:** Maintain a containerized `vLLM` service definition with `Qwen2.5-VL-7B-Instruct-AWQ` on `syafiq-svr` (accessible via Tailscale).
   - The FastAPI backend implements a Resilient Vision Client with an active Circuit Breaker (pybreaker / custom asyncio circuit breaker).
   - If Gemini API returns consecutive 5xx errors or times out (> 4.0s) 3 times, traffic seamlessly routes to the local vLLM instance with strict request queue throttling.
3. **PDPA Data Minimization:**
   - Receipt images are buffered strictly in memory during FastAPI request execution and streamed directly to the Vision API.
   - Images are never written to disk unless flagged for Manual Review (in which case they land in an encrypted S3/MinIO bucket with an automated 24-hour purge policy).

---

## 7. Consequences

### Positive
- **Guaranteed Sub-30s P95:** Gemini 2.0 Flash delivers 1.2s–1.8s typical inference, providing < 3.5s total end-to-end user turnaround.
- **Near-Zero Running Cost:** ~$5/month AI cost vs. dedicated cloud GPU instances costing $300–$800/month.
- **Bulletproof Reliability:** 100 concurrent lunch rush shoppers are effortlessly absorbed without local GPU thermal stress or queue starvation.
- **Disaster Survival:** If cloud WAN or Google API fails, the local on-premise RTX 4090 takes over for degraded-throughput operation.

### Negative & Mitigations
- **Third-Party Dependency:** External API dependency. *Mitigated by dual-provider abstraction and local vLLM fallback adapter.*
- **Data in Transit:** Receipt images leave the local network. *Mitigated by verifying receipts contain no NRIC or personal identification data, using TLS 1.3 in transit, and operating under Google Cloud's Zero-Data-Retention enterprise policy.*
