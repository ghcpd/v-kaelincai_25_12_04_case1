# Structured Logging Schema & Observability

## 1. Logging Architecture

### Goals
- ✅ Trace prediction lifecycle via unique request_id
- ✅ Mask sensitive fields (image paths may contain PII)
- ✅ Capture all crash points for debugging
- ✅ Enable metrics collection and alerting
- ✅ Audit trail for compliance

### Log Levels

| Level | Usage | Example |
|-------|-------|---------|
| **DEBUG** | Detailed state transitions | `[DEBUG] Layer 1 activation range: [-0.5, 0.8]` |
| **INFO** | Normal operation milestone | `[INFO] Prediction completed: digit=7, confidence=0.89` |
| **WARN** | Degraded but recoverable | `[WARN] Image resize needed; original size 30x30` |
| **ERROR** | Expected failure mode | `[ERROR] File not found: {path_hash}` |
| **CRITICAL** | Unexpected system failure | `[CRITICAL] Circuit breaker opened; too many timeouts` |

---

## 2. Core Logging Schema (JSON)

### Prediction Request Log

```json
{
  "timestamp": "2025-12-03T10:45:23.123456Z",
  "request_id": "req_7a3f8e2b-4c1d-11ec-81d3-0242ac130003",
  "event_type": "prediction_started",
  "level": "INFO",
  
  "request": {
    "image_path_hash": "sha256_abc123...",
    "image_path_length": 32,
    "timeout_ms": 5000,
    "retry_policy": {
      "max_retries": 3,
      "backoff_ms": [100, 200, 400]
    }
  },
  
  "trace_id": "trace_7a3f8e2b",
  "span_id": "span_001"
}
```

### Preprocessing Log

```json
{
  "timestamp": "2025-12-03T10:45:23.234567Z",
  "request_id": "req_7a3f8e2b-4c1d-11ec-81d3-0242ac130003",
  "event_type": "preprocessing_completed",
  "level": "INFO",
  
  "preprocessing": {
    "stage": "normalization",
    "input_shape": [28, 28],
    "output_shape": [784],
    
    "pixel_statistics": {
      "min": 0.0,
      "max": 1.0,
      "mean": 0.45,
      "std": 0.32,
      "range": "valid"
    },
    
    "validation": {
      "normalization_applied": true,
      "range_check_passed": true,
      "assertions_passed": true
    },
    
    "processing_time_ms": 12
  },
  
  "trace_id": "trace_7a3f8e2b",
  "span_id": "span_002"
}
```

### Inference Log

```json
{
  "timestamp": "2025-12-03T10:45:23.356789Z",
  "request_id": "req_7a3f8e2b-4c1d-11ec-81d3-0242ac130003",
  "event_type": "inference_completed",
  "level": "INFO",
  
  "inference": {
    "layer1": {
      "input_shape": [784],
      "output_shape": [128],
      "activation": "relu",
      "min_activation": -0.02,
      "max_activation": 0.78,
      "mean_activation": 0.15
    },
    
    "layer2": {
      "input_shape": [128],
      "output_shape": [10],
      "activation": "softmax",
      "output_range": [0.01, 0.89],
      "sum": 0.9999
    },
    
    "processing_time_ms": 8
  },
  
  "trace_id": "trace_7a3f8e2b",
  "span_id": "span_003"
}
```

### Prediction Result Log

```json
{
  "timestamp": "2025-12-03T10:45:23.456789Z",
  "request_id": "req_7a3f8e2b-4c1d-11ec-81d3-0242ac130003",
  "event_type": "prediction_completed",
  "level": "INFO",
  
  "result": {
    "status": "success",
    "prediction": 7,
    "confidence": 0.89,
    
    "probabilities": {
      "digit_0": 0.01,
      "digit_1": 0.02,
      "digit_2": 0.01,
      "digit_3": 0.01,
      "digit_4": 0.02,
      "digit_5": 0.01,
      "digit_6": 0.02,
      "digit_7": 0.89,
      "digit_8": 0.00,
      "digit_9": 0.01
    }
  },
  
  "retry_info": {
    "retry_count": 0,
    "backoff_sequence": []
  },
  
  "performance": {
    "total_latency_ms": 45,
    "preprocessing_ms": 12,
    "inference_ms": 8,
    "logging_ms": 2,
    "other_ms": 23
  },
  
  "trace_id": "trace_7a3f8e2b",
  "span_id": "span_004"
}
```

### Error Log

```json
{
  "timestamp": "2025-12-03T10:45:24.567890Z",
  "request_id": "req_error_001-4c1d-11ec-81d3-0242ac130003",
  "event_type": "prediction_failed",
  "level": "ERROR",
  
  "error": {
    "error_code": "FILE_NOT_FOUND",
    "error_message": "Image file does not exist",
    "error_type": "FileNotFoundError",
    
    "context": {
      "image_path_hash": "sha256_def456...",
      "attempted_retry": 3,
      "max_retries": 3
    },
    
    "stack_trace": "Traceback (most recent call last):\n  File \"src/prediction_service.py\", line 42, in load_image\n    with open(image_path) as f:\nFileNotFoundError: [Errno 2] No such file or directory",
    
    "recovery_action": "Failed; no fallback available"
  },
  
  "retry_info": {
    "retry_count": 3,
    "backoff_applied": [100, 200, 400],
    "total_retry_time_ms": 700
  },
  
  "trace_id": "trace_error_001",
  "span_id": "span_error_001"
}
```

### Audit Log (Outbox Entry)

```json
{
  "timestamp": "2025-12-03T10:45:23.600000Z",
  "request_id": "req_7a3f8e2b-4c1d-11ec-81d3-0242ac130003",
  "event_type": "audit_prediction_recorded",
  "level": "INFO",
  
  "audit_record": {
    "idempotency_key": "req_7a3f8e2b-4c1d-11ec-81d3-0242ac130003",
    "image_path_hash": "sha256_abc123...",
    
    "prediction_details": {
      "prediction": 7,
      "confidence": 0.89,
      "probabilities_hash": "sha256_prob123...",
      "top_5_predictions": [
        {"digit": 7, "prob": 0.89},
        {"digit": 6, "prob": 0.02},
        {"digit": 1, "prob": 0.02},
        {"digit": 4, "prob": 0.02},
        {"digit": 8, "prob": 0.00}
      ]
    },
    
    "preprocessing_metadata": {
      "pixel_range_min": 0.0,
      "pixel_range_max": 1.0,
      "normalization_applied": true,
      "validation_passed": true
    },
    
    "performance_metrics": {
      "total_latency_ms": 45,
      "preprocessing_ms": 12,
      "inference_ms": 8
    },
    
    "status": "success",
    "retry_count": 0
  },
  
  "trace_id": "trace_7a3f8e2b",
  "span_id": "span_audit_001"
}
```

---

## 3. Sensitive Field Masking

### Fields to Mask

| Field | Original | Masked |
|-------|----------|--------|
| `image_path` | `/home/user/photos/2025-12-03_receipt.png` | `sha256_a1b2c3...` (hash only) |
| `probabilities` | `[0.01, 0.02, ..., 0.89]` | Hash or omitted |
| Model weights | Not logged | N/A |
| User metadata | N/A | N/A |

### Masking Implementation

```python
import hashlib
import json

def mask_sensitive_fields(log_dict):
    """Mask PII and sensitive fields in log."""
    
    # Mask image paths
    if 'request' in log_dict and 'image_path' in log_dict['request']:
        path = log_dict['request']['image_path']
        path_hash = hashlib.sha256(path.encode()).hexdigest()[:16]
        log_dict['request']['image_path_hash'] = f"sha256_{path_hash}"
        del log_dict['request']['image_path']
    
    # Mask full probability arrays (keep only top-5)
    if 'result' in log_dict and 'probabilities' in log_dict['result']:
        probs = log_dict['result']['probabilities']
        # Reduce to top-5 predictions
        top_5 = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:5]
        log_dict['result']['probabilities_top_5'] = dict(top_5)
        del log_dict['result']['probabilities']
    
    return log_dict
```

---

## 4. Distributed Tracing (trace_id & span_id)

### Trace Flow

```
Request: req_7a3f8e2b-4c1d-11ec-81d3-0242ac130003
  │
  ├─ Span 1: Request Validation [0-2ms]
  │  └─ trace_id: trace_7a3f8e2b
  │  └─ span_id: span_001
  │  └─ parent_span_id: null
  │
  ├─ Span 2: Preprocessing [2-14ms]
  │  └─ trace_id: trace_7a3f8e2b
  │  └─ span_id: span_002
  │  └─ parent_span_id: span_001
  │
  ├─ Span 3: Inference [14-22ms]
  │  └─ trace_id: trace_7a3f8e2b
  │  └─ span_id: span_003
  │  └─ parent_span_id: span_001
  │
  └─ Span 4: Logging [22-24ms]
     └─ trace_id: trace_7a3f8e2b
     └─ span_id: span_004
     └─ parent_span_id: span_001

Total Latency: 24ms (trace completed)
```

---

## 5. Metrics Schema

### Metrics Emitted

```
# Latency (histogram)
prediction_latency_ms:
  ├─ min: 40.5
  ├─ p50: 48.2
  ├─ p95: 62.1
  ├─ p99: 89.3
  └─ max: 125.4

# Error Rate (counter)
prediction_errors_total:
  ├─ FILE_NOT_FOUND: 3
  ├─ INVALID_IMAGE_FORMAT: 1
  ├─ TIMEOUT: 2
  └─ INTERNAL_ERROR: 0

# Retry Rate (counter)
prediction_retries_total: 12  # 12 retries across all requests

# Circuit Breaker (gauge)
circuit_breaker_state:
  ├─ CLOSED: 1 (normal)
  ├─ OPEN: 0
  └─ HALF_OPEN: 0

# Idempotency (counter)
idempotency_cache_hits: 45  # 45 requests returned from cache

# Accuracy (if ground truth available)
prediction_accuracy:
  ├─ total: 1000
  ├─ correct: 950
  ├─ accuracy: 95.0%
  └─ by_digit: {0: 0.92, 1: 0.95, ..., 9: 0.96}
```

---

## 6. Log Output Examples

### Example 1: Successful Prediction

```log
2025-12-03T10:45:23.123Z [INFO] [req_7a3f8e2b] Prediction started
  image_path_hash: sha256_a1b2c3d4
  timeout_ms: 5000

2025-12-03T10:45:23.135Z [INFO] [req_7a3f8e2b] Preprocessing completed
  pixel_min: 0.0, pixel_max: 1.0 ✅ VALID
  normalization_applied: true
  validation_passed: true
  processing_ms: 12

2025-12-03T10:45:23.143Z [INFO] [req_7a3f8e2b] Inference completed
  layer1_activation_range: [-0.02, 0.78]
  layer2_output_range: [0.01, 0.89]
  processing_ms: 8

2025-12-03T10:45:23.150Z [INFO] [req_7a3f8e2b] Prediction result
  status: success
  prediction: 7
  confidence: 0.89
  probabilities_top_5: {7: 0.89, 6: 0.02, 1: 0.02, 4: 0.02, 8: 0.00}
  total_latency_ms: 27
  retry_count: 0

2025-12-03T10:45:23.152Z [INFO] [req_7a3f8e2b] Audit recorded
  idempotency_key: req_7a3f8e2b
  status: success
  trace_id: trace_7a3f8e2b
```

### Example 2: Retry on Transient Error

```log
2025-12-03T10:45:24.100Z [INFO] [req_retry_001] Prediction started
  image_path_hash: sha256_b2c3d4e5
  timeout_ms: 5000

2025-12-03T10:45:24.102Z [WARN] [req_retry_001] File I/O timeout on attempt 1
  error: TimeoutError
  elapsed_ms: 2001
  action: Retry with backoff

2025-12-03T10:45:24.310Z [WARN] [req_retry_001] File I/O timeout on attempt 2
  error: TimeoutError
  elapsed_ms: 2002
  backoff_applied_ms: 200
  action: Retry with backoff

2025-12-03T10:45:24.710Z [INFO] [req_retry_001] File I/O succeeded on attempt 3
  elapsed_ms: 50
  backoff_total_ms: 200

2025-12-03T10:45:24.722Z [INFO] [req_retry_001] Preprocessing completed
  validation_passed: true
  processing_ms: 12

2025-12-03T10:45:24.730Z [INFO] [req_retry_001] Prediction result
  status: success
  prediction: 7
  confidence: 0.89
  total_latency_ms: 630  (includes retry time)
  retry_count: 2  ← Key metric
```

### Example 3: Idempotency Cache Hit

```log
2025-12-03T10:45:25.100Z [INFO] [req_cache_001] Prediction started
  image_path_hash: sha256_c3d4e5f6
  request_id: req_cache_001

2025-12-03T10:45:25.101Z [INFO] [req_cache_001] Idempotency check
  previous_request_found: true
  cached_status: success
  cached_prediction: 7
  cached_confidence: 0.89
  action: Return cached result

2025-12-03T10:45:25.102Z [INFO] [req_cache_001] Returning cached prediction
  status: success
  prediction: 7
  confidence: 0.89
  total_latency_ms: 2  ← Cache hit is instant
  cache_hit: true
```

---

## 7. Alert Rules

### Alert: High Error Rate

```
alert: PredictionHighErrorRate
  condition: |
    (prediction_errors_total[5m] / prediction_requests_total[5m]) > 0.05
  severity: critical
  annotation: |
    Error rate exceeds 5% over last 5 minutes
    Investigate: circuit_breaker_state, timeout_errors, file_not_found_errors
```

### Alert: High Latency

```
alert: PredictionHighLatency
  condition: |
    prediction_latency_ms_p95[5m] > 300
  severity: warning
  annotation: |
    p95 latency exceeds 300ms SLA
    Investigate: I/O performance, model inference time
```

### Alert: Circuit Breaker Open

```
alert: CircuitBreakerOpen
  condition: |
    circuit_breaker_state == "OPEN"
  severity: critical
  annotation: |
    Circuit breaker is OPEN; service rejecting requests
    Action: Page on-call, check system health, consider fallback
```

---

## Summary

**Logging Enables**:
- ✅ Root cause analysis (via detailed context)
- ✅ Performance monitoring (latency, errors)
- ✅ Idempotency validation (request_id tracing)
- ✅ Compliance (audit trail, field masking)
- ✅ Distributed tracing (trace_id, span_id)
- ✅ Alerting (thresholds on metrics)

**Sensitive Fields Protected**:
- Image paths hashed (PII)
- Probabilities aggregated (reduced detail)
- Stack traces sanitized

**Metrics Collected**:
- Latency, errors, retries, cache hits, accuracy

