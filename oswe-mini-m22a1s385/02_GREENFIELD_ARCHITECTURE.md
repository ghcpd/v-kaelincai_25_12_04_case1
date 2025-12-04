# Greenfield Architecture Design: MNIST Classifier v2

## Overview

This document describes the v2 system, a **reliability-first redesign** of the legacy MNIST classifier that eliminates the v1.1 preprocessing bug through architectural patterns: unified state machine, idempotency keys, retry/timeout/circuit-breaker, transactional outbox, and structured observability.

---

## 1. Target State & Capability Boundaries

### Functional Capabilities

```
MNIST Classifier v2
├── Input: Image file path (local/remote)
├── Processing:
│   ├── Load & validate image format/size
│   ├── Preprocess with strict range validation
│   ├── Inference (forward pass)
│   └── Confidence scoring
├── Output: Predicted digit (0-9) + confidence + audit trail
└── Reliability: Idempotent, retriable, timeouts, observability
```

### Quality Attributes

| Attribute | v1 | v2 | Mechanism |
|-----------|----|----|-----------|
| **Correctness** | ❌ Broken (normalization bug) | ✅ Fixed (strict validation) | Unit tests + assertions |
| **Idempotency** | ⚠️ Deterministic but wrong | ✅ Correct + deterministic | Same (request_id independent) |
| **Reliability** | ❌ No retry | ✅ Retry + backoff | Exponential backoff + circuit breaker |
| **Observability** | ❌ print() only | ✅ Structured logs + metrics | JSON logging + request tracing |
| **Testability** | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Excellent | Mock API, fixtures, reproducible data |

---

## 2. Service Decomposition

### v2 Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    Client / Orchestrator                         │
└────────────────────┬────────────────────────────────────────────┘
                     │
     ┌───────────────┴────────────────┐
     │ Request Validation Layer       │
     │ ├─ Schema validation           │
     │ ├─ Request ID generation       │
     │ └─ Timeout wrapper             │
     └───────────────┬────────────────┘
                     │
     ┌───────────────┴────────────────┐
     │ Circuit Breaker + Retry        │
     │ ├─ Exponential backoff         │
     │ ├─ Max retry limit (3)         │
     │ └─ Failure tracking            │
     └───────────────┬────────────────┘
                     │
     ┌───────────────┴────────────────┐
     │ Prediction Service (v2)        │
     │ ├─ Image load (with timeout)   │
     │ ├─ Preprocess (strict range)   │
     │ ├─ Inference                   │
     │ └─ Confidence scoring          │
     └───────────────┬────────────────┘
                     │
     ┌───────────────┴────────────────┐
     │ State Machine & Logging        │
     │ ├─ Unified state tracking      │
     │ ├─ Transactional outbox        │
     │ ├─ Audit events               │
     │ └─ Metrics emission            │
     └───────────────┬────────────────┘
                     │
     ┌───────────────┴────────────────┐
     │ Persistence Layer (Mock v1)    │
     │ ├─ Mock API /api/v2/predict   │
     │ ├─ Audit log store            │
     │ └─ Metrics time-series        │
     └─────────────────────────────────┘
```

### Service Contracts

#### **Prediction Service (v2)**

**Input**
```json
{
  "request_id": "req_7a3f8e2b-4c1d-11ec-81d3-0242ac130003",
  "image_path": "/data/test_digit_7.png",
  "timeout_ms": 5000,
  "retry_policy": {
    "max_retries": 3,
    "backoff_ms": [100, 200, 400]
  }
}
```

**Output (Success)**
```json
{
  "request_id": "req_7a3f8e2b-4c1d-11ec-81d3-0242ac130003",
  "status": "success",
  "prediction": 7,
  "confidence": 0.89,
  "probabilities": [0.01, 0.02, ..., 0.89, 0.01],
  "preprocessing": {
    "image_shape": [28, 28],
    "pixel_range": [0.0, 1.0],
    "validation_passed": true
  },
  "latency_ms": 45,
  "timestamp": "2025-12-03T10:45:23.123Z"
}
```

**Output (Failure)**
```json
{
  "request_id": "req_7a3f8e2b-4c1d-11ec-81d3-0242ac130003",
  "status": "failed",
  "error_code": "FILE_NOT_FOUND",
  "error_message": "Image file does not exist: /data/missing.png",
  "retry_count": 3,
  "timestamp": "2025-12-03T10:45:23.456Z"
}
```

---

## 3. Unified State Machine

```
START
  │
  ├─→ [INIT]
  │   └─ Action: Validate request schema
  │   └─ Transition: INIT → VALIDATING
  │
  ├─→ [VALIDATING]
  │   └─ Action: Check image_path, timeout_ms, retry_policy
  │   ├─ Success: → LOADING
  │   └─ Failure: → FAILED (validation error)
  │
  ├─→ [LOADING] {retry loop starts}
  │   └─ Action: Read image file (with timeout)
  │   ├─ Success: → RESIZING
  │   ├─ Timeout: → RETRY_WAIT (if retries left) or FAILED
  │   └─ IO Error: → RETRY_WAIT (if retries left) or FAILED
  │
  ├─→ [RESIZING]
  │   └─ Action: Resize to 28×28 if needed
  │   ├─ Success: → PREPROCESSING
  │   └─ Failure: → FAILED (invalid image)
  │
  ├─→ [PREPROCESSING]
  │   └─ Action: Array conversion + NORMALIZATION ✅ (fix bug here)
  │   ├─ Assertion: max(pixels) ≤ 1.0, min(pixels) ≥ 0.0
  │   ├─ Success: → RANGE_VALIDATION
  │   └─ Failure: → FAILED (normalization not applied)
  │
  ├─→ [RANGE_VALIDATION] {safety guard}
  │   └─ Action: Assert preprocessed range [0, 1]
  │   ├─ Success: → INFERENCE
  │   └─ Failure: → FAILED (preprocessing range invalid)
  │
  ├─→ [INFERENCE]
  │   └─ Action: Forward pass (layer1 + layer2)
  │   ├─ Success: → CONFIDENCE_SCORING
  │   └─ Failure: → FAILED (arithmetic error)
  │
  ├─→ [CONFIDENCE_SCORING]
  │   └─ Action: Softmax → argmax + max probability
  │   ├─ Assertion: 0 ≤ confidence ≤ 1.0
  │   ├─ Success: → AUDIT_LOGGING
  │   └─ Failure: → FAILED (confidence out of range)
  │
  ├─→ [AUDIT_LOGGING]
  │   └─ Action: Emit structured log + outbox event
  │   ├─ Success: → SUCCESS
  │   └─ Failure: → SUCCESS (partial; log not critical)
  │
  ├─→ [SUCCESS]
  │   └─ Return: Prediction + confidence + metadata
  │   └─ Emit: Metrics (latency, accuracy if known)
  │   └─ Transition: → END
  │
  ├─→ [RETRY_WAIT] {exponential backoff}
  │   └─ Action: Wait backoff[retry_count] ms
  │   ├─ Timeout: → LOADING (retry_count++)
  │   └─ Max reached: → FAILED (exhausted retries)
  │
  ├─→ [FAILED]
  │   └─ Action: Log error + emit failure event
  │   └─ Return: Error response
  │   └─ Transition: → END
  │
  └─→ END

Transitions Summary:
  INIT → VALIDATING → LOADING → RESIZING → PREPROCESSING 
       → RANGE_VALIDATION → INFERENCE → CONFIDENCE_SCORING 
       → AUDIT_LOGGING → SUCCESS → END

Retry Loop:
  (LOADING → RETRY_WAIT → LOADING) up to max_retries times
  or jump to FAILED on exhaustion
```

---

## 4. Idempotency & Retry Strategy

### Idempotency Design

**Idempotency Key**: `request_id` (UUID v4)

**Idempotency Check**:
```
Request comes in with request_id = "req_7a3f8e2b"
  ├─ Query outbox log: SELECT * FROM prediction_audit WHERE request_id = ?
  ├─ If found:
  │   └─ Check status:
  │       ├─ SUCCESS: Return cached result (same prediction + confidence)
  │       ├─ FAILED: Return error (do NOT retry)
  │       └─ PENDING: Wait for completion (max 30s) or timeout
  └─ If not found: Execute prediction (first attempt)
```

**Why Idempotent?**
- Same image + same model weights = same preprocessing and inference output
- No side effects (read-only; no state mutation)
- Safe to retry multiple times; client sees consistent result
- Stateless design allows horizontal scaling

### Retry Strategy

**Exponential Backoff with Jitter**

```python
def retry_with_backoff(max_retries=3, base_ms=100):
    backoff_ms = [100, 200, 400]  # Hardcoded for MNIST (simple case)
    
    for attempt in range(max_retries):
        try:
            result = load_and_predict(image_path)
            return result
        except (TimeoutError, IOError) as e:
            if attempt < max_retries - 1:
                wait_time = backoff_ms[attempt] + random.randint(0, 50)
                time.sleep(wait_time / 1000.0)
                continue
            else:
                raise PredictionFailed(f"Max retries exceeded: {e}")
```

**Retry Conditions**:
- ✅ Transient errors (file I/O timeout, network timeout)
- ❌ Permanent errors (file not found, invalid image format, model corrupt)
- ❌ Normalization bug (deterministic failure; retry won't help)

---

## 5. Timeout & Circuit Breaker

### Timeout Strategy

```
Request timeout: 5000 ms total
  ├─ File I/O timeout: 2000 ms (load image)
  ├─ Preprocessing timeout: 500 ms (resize, normalize)
  ├─ Inference timeout: 1000 ms (forward pass)
  ├─ Logging timeout: 500 ms (audit event)
  └─ Buffer: 500 ms (overhead)

Timeout enforcement:
  ├─ Wrapper: contextlib.timeout(timeout_ms)
  ├─ Exception: TimeoutError → retry or fail
  └─ Fallback: Partial result (prediction + "timeout" flag)
```

### Circuit Breaker

```
State Machine:
  CLOSED → OPEN → HALF_OPEN → (CLOSED or OPEN)

Triggers:
  ├─ CLOSED → OPEN: 5 consecutive failures in 60s window
  ├─ OPEN → HALF_OPEN: 30s elapsed without traffic
  └─ HALF_OPEN → CLOSED: 1 successful request

Behavior:
  ├─ CLOSED: Accept all requests (normal)
  ├─ OPEN: Reject with circuit breaker error (fail fast)
  └─ HALF_OPEN: Accept 1 test request; monitor result

Config:
  failure_threshold: 5
  success_threshold: 1
  timeout: 30s
  window: 60s
```

---

## 6. Transactional Outbox Pattern

### Problem Solved
- Audit events must be logged even if service crashes
- Ensures exactly-once semantics for predictions
- Enables reconciliation and replay

### Implementation

```python
# Prediction Service (v2)
class PredictionService:
    def predict(self, request):
        with transaction.begin():
            # Step 1: Execute prediction (in-memory)
            result = self._do_inference(request)
            
            # Step 2: Write to outbox (same transaction)
            outbox_entry = {
                "request_id": request.request_id,
                "status": "success",
                "prediction": result.prediction,
                "timestamp": now(),
                "idempotency_key": request.request_id
            }
            self.outbox_store.insert(outbox_entry)
            
            # Step 3: Commit both together
            transaction.commit()
        
        # Step 4: Emit event asynchronously (best-effort)
        self.event_bus.emit("PredictionCompleted", outbox_entry)
        
        return result
```

### Outbox Schema

```sql
-- prediction_audit table
CREATE TABLE prediction_audit (
    request_id UUID PRIMARY KEY,
    image_path VARCHAR(1024) NOT NULL,
    prediction INT NOT NULL,
    confidence FLOAT NOT NULL,
    preprocessing_max FLOAT NOT NULL,
    preprocessing_min FLOAT NOT NULL,
    latency_ms INT NOT NULL,
    status VARCHAR(20) NOT NULL,  -- 'success', 'failed'
    error_code VARCHAR(50),
    retry_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for idempotency checks
CREATE UNIQUE INDEX idx_request_id ON prediction_audit(request_id);
CREATE INDEX idx_status ON prediction_audit(status);
```

---

## 7. Compensation & Saga Pattern (Future)

### Not Required for v2 (Stateless)

Current system is **read-only**; no state to compensate.

```
If deployed as part of larger system (e.g., document processing):
  
  Saga: Process Document
    ├─ Step 1: Scan document → extract image
    │  └─ Compensation: Delete extracted image
    │
    ├─ Step 2: Predict digit (v2) ← CURRENT
    │  └─ Compensation: Mark prediction as "voided"
    │
    ├─ Step 3: Update database with prediction
    │  └─ Compensation: Delete database record
    │
    └─ If any step fails:
       ├─ Rollback in reverse order (3 → 2 → 1)
       └─ Log compensation events to outbox
```

---

## 8. API & Data Contracts

### REST API (Mock v2)

**Endpoint**: `POST /api/v2/predict`

**Request Schema**
```json
{
  "type": "object",
  "required": ["image_path"],
  "properties": {
    "request_id": {
      "type": "string",
      "pattern": "^req_[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}$",
      "description": "UUID v4 for idempotency"
    },
    "image_path": {
      "type": "string",
      "minLength": 1,
      "maxLength": 1024,
      "description": "Path to 28x28 grayscale PNG"
    },
    "timeout_ms": {
      "type": "integer",
      "minimum": 1000,
      "maximum": 30000,
      "default": 5000
    },
    "retry_policy": {
      "type": "object",
      "properties": {
        "max_retries": {
          "type": "integer",
          "minimum": 0,
          "maximum": 5,
          "default": 3
        },
        "backoff_ms": {
          "type": "array",
          "items": {"type": "integer", "minimum": 0},
          "default": [100, 200, 400]
        }
      }
    }
  }
}
```

**Response Schema (Success)**
```json
{
  "type": "object",
  "properties": {
    "request_id": {"type": "string"},
    "status": {"enum": ["success"]},
    "prediction": {
      "type": "integer",
      "minimum": 0,
      "maximum": 9
    },
    "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    },
    "probabilities": {
      "type": "array",
      "items": {"type": "number", "minimum": 0.0, "maximum": 1.0},
      "minItems": 10,
      "maxItems": 10
    },
    "preprocessing": {
      "type": "object",
      "properties": {
        "image_shape": {"type": "array", "items": {"type": "integer"}},
        "pixel_range": {
          "type": "array",
          "items": {"type": "number"},
          "minItems": 2,
          "maxItems": 2,
          "description": "[min, max] of preprocessed pixels"
        },
        "validation_passed": {"type": "boolean"}
      }
    },
    "latency_ms": {"type": "integer"},
    "timestamp": {"type": "string", "format": "date-time"}
  }
}
```

**Response Schema (Failure)**
```json
{
  "type": "object",
  "properties": {
    "request_id": {"type": "string"},
    "status": {"enum": ["failed"]},
    "error_code": {
      "enum": [
        "INVALID_REQUEST",
        "FILE_NOT_FOUND",
        "INVALID_IMAGE_FORMAT",
        "IMAGE_TOO_LARGE",
        "PREPROCESSING_FAILED",
        "INFERENCE_FAILED",
        "TIMEOUT",
        "CIRCUIT_BREAKER_OPEN",
        "INTERNAL_ERROR"
      ]
    },
    "error_message": {"type": "string"},
    "retry_count": {"type": "integer"},
    "timestamp": {"type": "string", "format": "date-time"}
  }
}
```

---

## 9. Field Constraints & Validation

| Field | Type | Constraints | Validation | Sanitization |
|-------|------|-------------|------------|--------------|
| `request_id` | UUID | Format: `req_XXXXXXXX-...` | Regex pattern match | N/A (generated) |
| `image_path` | String | 1–1024 chars | Not null, length | Trim whitespace |
| `timeout_ms` | Int | 1000–30000 | Range check | Default to 5000 |
| `max_retries` | Int | 0–5 | Range check | Default to 3 |
| `prediction` | Int | 0–9 | Enum check | N/A |
| `confidence` | Float | [0.0, 1.0] | Range check | N/A |
| `pixel_range[0]` | Float | [0.0, 1.0] | Range check | Round to 6 decimals |
| `pixel_range[1]` | Float | [0.0, 1.0] | Range check | Round to 6 decimals |

---

## 10. Data Flow Diagram

```
┌──────────────────┐
│  Client Request  │
│  request_id,     │
│  image_path,     │
│  timeout_ms      │
└────────┬─────────┘
         │
         ▼
   ┌─────────────────────────┐
   │  Request Validation     │
   │  ├─ Schema check        │
   │  ├─ Path sanitization   │
   │  └─ ID generation       │
   └────────┬────────────────┘
            │
            ▼
   ┌──────────────────────────┐
   │  Idempotency Check       │
   │  Query outbox by req_id  │
   └────────┬─────────────────┘
            │
   ┌────────┴─────────────┐
   │                      │
   ▼                      ▼
[CACHED]            [NEW REQUEST]
[Return cached]     [Execute pipeline]
   │                      │
   │                      ▼
   │            ┌──────────────────┐
   │            │  Circuit Breaker │
   │            │  Check state     │
   │            └────────┬─────────┘
   │                     │
   │                     ▼
   │            ┌──────────────────┐
   │            │  Load Image      │
   │            │  (with timeout)  │
   │            └────────┬─────────┘
   │                     │
   │            ┌────────┴─────────┐
   │            │                  │
   │            ▼                  ▼
   │        [SUCCESS]          [FAIL/TIMEOUT]
   │            │                  │
   │            ▼                  ▼
   │        ┌────────┐      ┌─────────────┐
   │        │ Resize │      │ Retry Logic │
   │        └────┬───┘      │ or emit err │
   │             │          └─────┬───────┘
   │             ▼                │
   │        ┌─────────────────┐   │
   │        │ Preprocess ✅    │   │
   │        │ ├─ Array conv    │   │
   │        │ ├─ NORMALIZE ÷255│   │
   │        │ └─ Flatten       │   │
   │        └────────┬────────┘   │
   │                 │             │
   │                 ▼             │
   │        ┌──────────────────┐   │
   │        │ Range Validation │   │
   │        │ max ≤ 1.0 check  │   │
   │        └────────┬─────────┘   │
   │                 │              │
   │                 ▼              │
   │        ┌──────────────────┐    │
   │        │ Inference        │    │
   │        │ Layer 1 + Layer 2│    │
   │        └────────┬─────────┘    │
   │                 │               │
   │                 ▼               │
   │        ┌──────────────────┐     │
   │        │ Confidence Score │     │
   │        │ Softmax & Argmax │     │
   │        └────────┬─────────┘     │
   │                 │                │
   │                 ▼                │
   │        ┌──────────────────────┐  │
   │        │ Emit Audit Event     │  │
   │        │ to outbox store      │  │
   │        └────────┬─────────────┘  │
   │                 │                 │
   │                 ▼                 │
   │        ┌──────────────────────┐  │
   │        │ Emit Metrics         │  │
   │        │ (latency, accuracy)  │  │
   │        └────────┬─────────────┘  │
   │                 │                 │
   └─────────────┬───┴─────────────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Response Builder │
        │ ├─ status        │
        │ ├─ prediction    │
        │ ├─ confidence    │
        │ ├─ metadata      │
        │ └─ latency       │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ Client Response  │
        │ (JSON)           │
        └──────────────────┘
```

---

## 11. Migration & Dual-Write Strategy

### Phase 1: Shadow Mode (Week 1)
```
Production:  Image → v1 (MNIST Classifier)
            ├─ Return result to client (v1)
            └─ Also call v2 (shadow) for validation
            
v2 results logged but NOT returned to client
Metrics: Compare v1 vs v2 predictions, latency
Goal: Verify v2 correctness before switchover
```

### Phase 2: Canary (Week 2)
```
Production:  Image → v1 or v2 (10% → v2, 90% → v1)
            ├─ Client ID = "canary" → route to v2
            └─ Client ID = others → route to v1

Monitoring:
  ├─ v2 accuracy vs v1
  ├─ v2 latency
  ├─ v2 error rates
  └─ Audit log consistency
```

### Phase 3: Ramp-Up (Week 3-4)
```
Production:  Image → v1 or v2 (50% → v2, 50% → v1)
            └─ Gradually increase v2 traffic: 50% → 75% → 90% → 100%

Rollback plan:
  ├─ If v2 error rate > 1%: Revert to 0% v2
  ├─ If v2 latency > 150% of v1: Investigate
  └─ If v2 predictions differ > 5% from v1: Debug
```

### Phase 4: Full Cutover (Week 5+)
```
Production: Image → v2 (100%)
           └─ v1 kept as emergency fallback (no traffic)

Monitoring:
  ├─ v2 SLA: 95% success, p50 < 100ms, p95 < 300ms
  ├─ Audit log: 100% traceability
  └─ Idempotency: Zero duplicates in outbox
```

### Rollback Path

```
If critical issue in v2:
  1. Detect: Alerts trigger (error_rate > 5%)
  2. Decide: On-call reviews evidence
  3. Execute: Switch traffic back to v1
  4. Verify: Predictions restore to expected values
  5. Investigate: Post-mortem on v2 failure
  6. Deploy: Fixed v2 in shadow mode again
```

---

## Summary

**v2 Achieves**:
1. ✅ **Fixes preprocessing bug** – Normalization enforced + validated
2. ✅ **Idempotent** – Same request_id → same result always
3. ✅ **Retriable** – Exponential backoff for transient errors
4. ✅ **Resilient** – Timeout, circuit breaker, observability
5. ✅ **Auditable** – Outbox pattern, structured logging, traceability
6. ✅ **Testable** – Mock API, fixtures, integration tests

**Key Improvements**:
- Unified state machine with explicit transitions
- Validation guards (preprocessing range checks)
- Structured logging with request ID tracing
- Idempotency key support
- Retry + backoff + circuit breaker
- Transactional outbox for audit
- Dual-write migration strategy

