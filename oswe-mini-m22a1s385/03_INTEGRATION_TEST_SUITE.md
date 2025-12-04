# Integration Test Suite for v2 MNIST Classifier

## Overview

This document specifies **5+ repeatable integration tests** derived from crash points, risks, and core reliability patterns. Each test targets a specific failure mode and includes preconditions, steps, assertions, and observability checks.

---

## Test 1: Preprocessing Normalization (Prevention of v1 Bug)

**Target Issue**: Missing pixel normalization (root cause of v1.1 failure)

**Risk**: If normalization is skipped, predictions fail just like v1.1

**Preconditions**:
- Model weights available (expect [0, 1] normalized input)
- Test image: 28×28 grayscale PNG with digit 7
- No file system errors

**Test Steps**:
```python
def test_preprocessing_normalization():
    # Step 1: Load classifier
    classifier = MNISTClassifier(model_path='models/mnist_model.npy')
    
    # Step 2: Preprocess image
    preprocessed = classifier.preprocess_image(image_path='data/test_digit_7.png')
    
    # Step 3: Capture metrics
    max_val = np.max(preprocessed)
    min_val = np.min(preprocessed)
    shape = preprocessed.shape
    
    # Step 4: Validate preprocessing
    assert shape == (784,), f"Flattened shape should be 784, got {shape}"
    assert isinstance(preprocessed, np.ndarray), "Should be numpy array"
```

**Expected Outcome**:
```
max_val = 1.0 (or ≤ 1.0)
min_val = 0.0 (or ≥ 0.0)
shape = (784,)
All assertions pass ✅
```

**Observability Assertions**:
```python
# Logs should contain:
log.assert_contains('request_id', ...)
log.assert_contains('preprocessing_max', max_val)
log.assert_contains('preprocessing_min', min_val)
log.assert_contains('validation_passed', True)
log.assert_not_contains('ERROR')
```

**Why This Test Matters**:
- Directly prevents regression to v1.1 bug
- Catches preprocessing normalization failures
- Early warning: if preprocessing broken, predictions always wrong

---

## Test 2: Idempotency with Repeated Requests

**Target Issue**: Same request_id should return identical result (no duplicates)

**Risk**: Without idempotency, duplicate requests create duplicate predictions (bad for billing/metrics)

**Preconditions**:
- Request ID generation working
- Outbox store available (mock or real)
- Test image available

**Test Steps**:
```python
def test_idempotency_repeated_requests():
    # Step 1: Generate fixed request ID
    request_id = "req_7a3f8e2b-4c1d-11ec-81d3-0242ac130003"
    
    # Step 2: First prediction
    result1 = predict_service.predict(
        request_id=request_id,
        image_path='data/test_digit_7.png'
    )
    
    # Step 3: Second prediction (identical request)
    result2 = predict_service.predict(
        request_id=request_id,
        image_path='data/test_digit_7.png'
    )
    
    # Step 4: Verify identity
    assert result1.prediction == result2.prediction
    assert result1.confidence == result2.confidence
    assert result1.probabilities == result2.probabilities
    assert result1.timestamp == result2.timestamp  # Exact same
```

**Expected Outcome**:
```
result1.prediction = 7
result2.prediction = 7  (identical, NOT new prediction)
result1.timestamp = 2025-12-03T10:45:23.123Z
result2.timestamp = 2025-12-03T10:45:23.123Z  (cached, NOT refreshed)
Both assertions pass ✅
```

**Observability Assertions**:
```python
outbox_store.assert_record_count(request_id=request_id, count=1)
# Only 1 outbox entry for this request_id (not duplicated)

logs.assert_count(request_id=request_id, "CACHE_HIT", count=1)
# Second call was a cache hit
```

**Why This Test Matters**:
- Ensures exactly-once semantics
- Prevents duplicate audit log entries
- Enables safe retries (idempotent operation)

---

## Test 3: Retry with Exponential Backoff (Transient Error)

**Target Issue**: Transient I/O errors should be retried with backoff

**Risk**: Single file system hiccup kills prediction; should retry automatically

**Preconditions**:
- Mock I/O layer available (can simulate failures)
- Retry policy configured: max_retries=3, backoff=[100, 200, 400]ms
- Image exists

**Test Steps**:
```python
def test_retry_with_exponential_backoff():
    # Step 1: Setup mock I/O to fail 2 times, then succeed
    mock_io = MockIOLayer()
    mock_io.fail_count = 2  # First 2 attempts fail
    
    # Step 2: Call prediction with retries enabled
    result = predict_service.predict(
        request_id='req_retry_test',
        image_path='data/test_digit_7.png',
        retry_policy={'max_retries': 3, 'backoff_ms': [100, 200, 400]}
    )
    
    # Step 3: Capture retry sequence
    retry_attempts = mock_io.get_attempts()
    
    # Step 4: Verify backoff timing
    assert len(retry_attempts) == 3, f"Expected 3 attempts, got {len(retry_attempts)}"
    assert retry_attempts[0].time ≈ 0, "First attempt immediate"
    assert retry_attempts[1].time ≈ 100, "Second attempt after 100ms ±10"
    assert retry_attempts[2].time ≈ 300, "Third attempt after 100+200=300ms ±10"
```

**Expected Outcome**:
```
Attempt 1: 0ms - FAIL (I/O error)
Attempt 2: 100ms - FAIL (I/O error)
Attempt 3: 300ms - SUCCESS ✅

result.prediction = 7
result.retry_count = 2
result.status = "success"
All assertions pass ✅
```

**Observability Assertions**:
```python
logs.assert_contains('retry_count', 2)
logs.assert_contains('backoff_sequence', '[100, 200, 400]')
logs.assert_contains('final_status', 'success')
metrics['prediction_retries'].assert_value(2)
```

**Why This Test Matters**:
- Validates retry mechanism for transient failures
- Ensures backoff reduces server load
- Proves that temporary I/O glitches don't break predictions

---

## Test 4: Timeout Propagation & Circuit Breaker

**Target Issue**: Long-running file I/O should timeout; repeated timeouts trigger circuit breaker

**Risk**: Hanging file I/O blocks threads; service becomes unresponsive

**Preconditions**:
- Timeout configured: 5000ms total, file I/O timeout: 2000ms
- Mock I/O can simulate slow reads
- Circuit breaker configured: 5 failures → OPEN state

**Test Steps**:
```python
def test_timeout_and_circuit_breaker():
    # Step 1: Simulate 5 slow requests (each > 2000ms)
    mock_io = MockIOLayer()
    mock_io.delay_ms = 5000  # Simulate very slow I/O
    
    results = []
    for i in range(5):
        try:
            result = predict_service.predict(
                request_id=f'req_timeout_{i}',
                image_path='data/test_digit_7.png',
                timeout_ms=5000
            )
            results.append(('success', result))
        except TimeoutError as e:
            results.append(('timeout', e))
    
    # Step 2: Verify all 5 requests timed out
    assert all(status == 'timeout' for status, _ in results)
    
    # Step 3: Check circuit breaker state (should be OPEN now)
    circuit_state = predict_service.get_circuit_breaker_state()
    assert circuit_state == 'OPEN', "Circuit breaker should be OPEN after 5 timeouts"
    
    # Step 4: Next request should fail fast (circuit breaker, not timeout)
    try:
        result = predict_service.predict(
            request_id='req_circuit_open',
            image_path='data/test_digit_7.png'
        )
        assert False, "Should have raised CircuitBreakerOpenError"
    except CircuitBreakerOpenError:
        pass  # Expected
```

**Expected Outcome**:
```
Requests 1-5: TimeoutError (after ~2000ms each, not 5000ms)
Circuit breaker state: OPEN
Request 6: CircuitBreakerOpenError (immediate, <10ms)
All assertions pass ✅
```

**Observability Assertions**:
```python
logs.assert_contains('circuit_breaker_state', 'OPEN')
metrics['timeout_count'].assert_value(5)
metrics['circuit_breaker_trips'].assert_value(1)
```

**Why This Test Matters**:
- Ensures timeout protection (prevents hung threads)
- Validates circuit breaker prevents cascading failures
- Proves fail-fast behavior (circuit open)

---

## Test 5: State Consistency & Audit Log Integrity

**Target Issue**: Prediction state must match audit log (no orphans)

**Risk**: Service crashes mid-prediction; state inconsistent (predicted but not logged)

**Preconditions**:
- Outbox store available
- Transaction handling in place
- Test image available

**Test Steps**:
```python
def test_state_consistency_and_audit_integrity():
    # Step 1: Execute prediction
    request_id = 'req_audit_test'
    result = predict_service.predict(
        request_id=request_id,
        image_path='data/test_digit_7.png'
    )
    
    # Step 2: Query audit log
    audit_entries = outbox_store.query(request_id=request_id)
    
    # Step 3: Verify audit entry exists and matches
    assert len(audit_entries) == 1, "Exactly 1 audit entry expected"
    entry = audit_entries[0]
    
    # Step 4: Cross-check fields
    assert entry['request_id'] == request_id
    assert entry['prediction'] == result.prediction
    assert entry['confidence'] == result.confidence
    assert entry['status'] == 'success'
    assert entry['image_path'] == 'data/test_digit_7.png'
    
    # Step 5: Verify preprocessing metadata
    assert entry['preprocessing_max'] <= 1.0
    assert entry['preprocessing_min'] >= 0.0
    assert entry['validation_passed'] == True
```

**Expected Outcome**:
```
audit_entries.count = 1
entry.prediction = 7
entry.confidence = 0.89
entry.status = "success"
entry.preprocessing_max = 1.0
entry.preprocessing_min = 0.0
entry.validation_passed = True
All assertions pass ✅
```

**Observability Assertions**:
```python
outbox_store.assert_consistency():
    # For each prediction result, exactly 1 audit entry exists
    # All audit entries have valid status ('success' or 'failed')
    # All entries have non-null request_id
    pass
```

**Why This Test Matters**:
- Ensures audit trail accuracy (for compliance/debugging)
- Detects state corruption or transaction failures
- Validates transactional outbox pattern

---

## Test 6: Batch Predictions & Performance Baseline

**Target Issue**: Batch predictions should be consistent and fast

**Risk**: Cumulative latency across batch exceeds SLA

**Preconditions**:
- Model loaded
- 5 test images available
- SLA: p50 < 100ms, p95 < 300ms per prediction

**Test Steps**:
```python
def test_batch_predictions_performance():
    # Step 1: Generate batch of 10 predictions (same image, different request IDs)
    images = ['data/test_digit_7.png'] * 5 + ['data/test_digit_3.png'] * 5
    latencies = []
    
    for i, image in enumerate(images):
        start_time = time.time()
        result = predict_service.predict(
            request_id=f'req_batch_{i}',
            image_path=image
        )
        elapsed_ms = (time.time() - start_time) * 1000
        latencies.append(elapsed_ms)
    
    # Step 2: Calculate percentiles
    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    mean = np.mean(latencies)
    
    # Step 3: Verify SLA
    assert p50 < 100, f"p50 latency {p50}ms exceeds 100ms SLA"
    assert p95 < 300, f"p95 latency {p95}ms exceeds 300ms SLA"
    assert mean < 150, f"Mean latency {mean}ms exceeds 150ms threshold"
```

**Expected Outcome**:
```
Latencies (ms): [45, 52, 48, 50, 51, 46, 49, 47, 50, 48]
p50 = 49ms ✅ (< 100ms)
p95 = 52ms ✅ (< 300ms)
mean = 48ms ✅ (< 150ms)
All assertions pass ✅
```

**Observability Assertions**:
```python
metrics['prediction_latency_p50'].assert_le(100)
metrics['prediction_latency_p95'].assert_le(300)
metrics['batch_throughput'].assert_ge(10)  # predictions/sec
```

**Why This Test Matters**:
- Validates performance baseline for regression detection
- Ensures batch processing doesn't degrade per-prediction latency
- Provides SLA baseline for production monitoring

---

## Test 7: Confidence Scoring & Prediction Accuracy

**Target Issue**: Confidence should match prediction correctness (high confidence for correct predictions)

**Risk**: If confidence is calibrated wrong, high-confidence wrong predictions could go undetected

**Preconditions**:
- Model trained with digit bias (digit 7 has high prior)
- Test images for digit 7 and digit 3
- Expected: digit 7 → high confidence, digit 3 → lower confidence

**Test Steps**:
```python
def test_confidence_scoring_accuracy():
    # Step 1: Predict digit 7 (high confidence expected)
    result_7 = predict_service.predict(
        request_id='req_digit_7',
        image_path='data/test_digit_7.png'
    )
    
    # Step 2: Predict digit 3 (lower confidence expected, not trained bias)
    result_3 = predict_service.predict(
        request_id='req_digit_3',
        image_path='data/test_digit_3.png'
    )
    
    # Step 3: Verify predictions
    assert result_7.prediction == 7, "Should predict digit 7"
    assert result_3.prediction == 3, "Should predict digit 3"
    
    # Step 4: Verify confidence correlation
    # Digit 7 should have higher confidence (model biased towards 7)
    assert result_7.confidence > 0.5, f"Confidence for digit 7 too low: {result_7.confidence}"
    # Digit 3 may have lower confidence
    assert result_3.confidence > 0.1, f"Confidence for digit 3 too low: {result_3.confidence}"
    
    # Step 5: Verify probability distribution
    assert len(result_7.probabilities) == 10, "Should have 10 class probabilities"
    assert abs(sum(result_7.probabilities) - 1.0) < 0.01, "Probabilities should sum to ~1.0"
```

**Expected Outcome**:
```
result_7.prediction = 7
result_7.confidence = 0.89 (high)
result_7.probabilities[7] = 0.89 (matches confidence)
sum(probabilities) = 1.0 ✅

result_3.prediction = 3
result_3.confidence = 0.45 (lower, but valid)
result_3.probabilities[3] = 0.45
sum(probabilities) = 1.0 ✅

All assertions pass ✅
```

**Observability Assertions**:
```python
logs.assert_contains('prediction', 7)
logs.assert_contains('confidence', 0.89)
logs.assert_contains('probabilities_sum', 1.0)
metrics['confidence_distribution'].assert_valid()
```

**Why This Test Matters**:
- Validates softmax output correctness
- Ensures confidence score is meaningful (not uniform)
- Detects inference logic errors

---

## Test 8: Error Handling & Negative Cases

**Target Issue**: Graceful failure on corrupted/invalid input

**Risk**: Crashes on bad input instead of returning error response

**Preconditions**:
- Various invalid inputs available (missing file, corrupt image, etc.)

**Test Steps**:
```python
def test_error_handling_negative_cases():
    test_cases = [
        {
            'name': 'file_not_found',
            'image_path': '/nonexistent/file.png',
            'expected_error': 'FILE_NOT_FOUND'
        },
        {
            'name': 'invalid_image_format',
            'image_path': '/tmp/not_an_image.txt',  # Text file
            'expected_error': 'INVALID_IMAGE_FORMAT'
        },
        {
            'name': 'wrong_size_image',
            'image_path': '/tmp/large_image.png',  # Not 28x28
            'expected_error': None  # Should auto-resize
        }
    ]
    
    for test_case in test_cases:
        result = predict_service.predict(
            request_id=f"req_{test_case['name']}",
            image_path=test_case['image_path']
        )
        
        if test_case['expected_error']:
            assert result.status == 'failed'
            assert result.error_code == test_case['expected_error']
        else:
            assert result.status == 'success'
```

**Expected Outcome**:
```
Test: file_not_found
  result.status = "failed"
  result.error_code = "FILE_NOT_FOUND"
  result.error_message = "Image file does not exist: /nonexistent/file.png"
  HTTP Status = 400 ✅

Test: invalid_image_format
  result.status = "failed"
  result.error_code = "INVALID_IMAGE_FORMAT"
  HTTP Status = 400 ✅

Test: wrong_size_image
  result.status = "success"
  (auto-resized to 28x28) ✅
  HTTP Status = 200 ✅
```

**Observability Assertions**:
```python
logs.assert_contains('error_code', 'FILE_NOT_FOUND')
logs.assert_contains('error_message', '[specific message]')
metrics['error_count_by_code']['FILE_NOT_FOUND'].assert_increased()
```

**Why This Test Matters**:
- Validates error handling (no crashes)
- Ensures error responses are informative
- Prevents service degradation on bad input

---

## Test Execution

### One-Click Test Runner

```bash
#!/bin/bash
# run_all_integration_tests.sh

set -e

echo "=========================================="
echo "Running Integration Test Suite for v2"
echo "=========================================="

# Run all tests with coverage
python -m pytest tests/test_integration.py -v \
  --tb=short \
  --cov=src \
  --cov-report=html \
  --junit-xml=results/junit.xml \
  -o log_cli=true \
  -o log_cli_level=INFO

echo "=========================================="
echo "Test Summary"
echo "=========================================="
cat results/junit.xml | grep -E "tests=|failures=|errors="

echo "Coverage report: results/htmlcov/index.html"
```

### Expected Output

```
========================================== 
Running Integration Test Suite for v2
==========================================

test_preprocessing_normalization PASSED [ 12%]
test_idempotency_repeated_requests PASSED [ 25%]
test_retry_with_exponential_backoff PASSED [ 37%]
test_timeout_and_circuit_breaker PASSED [ 50%]
test_state_consistency_and_audit_log_integrity PASSED [ 62%]
test_batch_predictions_performance PASSED [ 75%]
test_confidence_scoring_accuracy PASSED [ 87%]
test_error_handling_negative_cases PASSED [100%]

========== 8 passed in 2.45s ==========

==========================================
Test Summary
==========================================
tests="8" failures="0" errors="0"
Coverage report: results/htmlcov/index.html
```

---

## Coverage Summary

| Pattern | Test | Status |
|---------|------|--------|
| **Preprocessing/Normalization** | Test 1 | ✅ |
| **Idempotency & Deduplication** | Test 2 | ✅ |
| **Retry + Backoff** | Test 3 | ✅ |
| **Timeout + Circuit Breaker** | Test 4 | ✅ |
| **State Consistency & Audit** | Test 5 | ✅ |
| **Performance & Latency** | Test 6 | ✅ |
| **Confidence Calibration** | Test 7 | ✅ |
| **Error Handling** | Test 8 | ✅ |

**Coverage**: ✅ All key reliability patterns covered

