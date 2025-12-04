"""
Mock REST API for MNIST Classifier v2

Simulates the /api/v2/predict endpoint for integration testing.
Supports idempotency, retries, timeouts, and circuit breaker patterns.
"""

import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from src_v2_mnist_classifier_v2 import (
    MNISTClassifierV2,
    PredictionRequest,
    PredictionResult,
    asdict
)


class MockAPIResponse:
    """Simulates HTTP response."""
    
    def __init__(self, status_code: int, body: Dict[str, Any]):
        self.status_code = status_code
        self.body = body
        self.headers = {"Content-Type": "application/json"}
    
    def to_json(self) -> str:
        return json.dumps(self.body, indent=2)
    
    def to_dict(self) -> Dict[str, Any]:
        return self.body


class MockMNISTAPI:
    """Mock REST API for v2 MNIST Classifier."""
    
    def __init__(self, model_path: str):
        self.classifier = MNISTClassifierV2(model_path)
    
    def predict(self, request_body: Dict[str, Any]) -> MockAPIResponse:
        """
        POST /api/v2/predict
        
        Request body:
        {
            "request_id": "req_uuid" (optional; generated if missing),
            "image_path": "/path/to/image.png" (required),
            "timeout_ms": 5000 (optional),
            "retry_policy": {
                "max_retries": 3 (optional),
                "backoff_ms": [100, 200, 400] (optional)
            }
        }
        
        Response body (success):
        {
            "request_id": "req_uuid",
            "status": "success",
            "prediction": 7,
            "confidence": 0.89,
            "probabilities": [0.01, 0.02, ..., 0.89, 0.01],
            "preprocessing": {
                "pixel_min": 0.0,
                "pixel_max": 1.0,
                "pixel_mean": 0.45,
                "normalization_applied": true,
                "validation_passed": true,
                "processing_time_ms": 12
            },
            "latency_ms": 45,
            "timestamp": "2025-12-03T10:45:23.456Z"
        }
        
        Response body (failure):
        {
            "request_id": "req_uuid",
            "status": "failed",
            "error_code": "FILE_NOT_FOUND",
            "error_message": "Image file does not exist",
            "retry_count": 3,
            "timestamp": "2025-12-03T10:45:23.456Z"
        }
        """
        
        try:
            # Validate request
            if not request_body.get("image_path"):
                request_id_val: str = request_body.get("request_id", f"req_{uuid.uuid4()}")
                return self._error_response(
                    status_code=400,
                    error_code="INVALID_REQUEST",
                    error_message="Missing required field: image_path",
                    request_id=request_id_val
                )
            
            # Generate request ID if not provided
            request_id = request_body.get("request_id", f"req_{uuid.uuid4()}")
            
            # Extract parameters
            image_path = request_body["image_path"]
            timeout_ms = request_body.get("timeout_ms", 5000)
            retry_policy = request_body.get("retry_policy", {})
            
            # Create prediction request
            pred_request = PredictionRequest(
                request_id=request_id,
                image_path=image_path,
                timeout_ms=timeout_ms,
                max_retries=retry_policy.get("max_retries", 3),
                backoff_ms=retry_policy.get("backoff_ms", [100, 200, 400])
            )
            
            # Execute prediction
            result = self.classifier.predict(pred_request)
            
            # Build response
            response_body = {
                "request_id": request_id,
                "status": result.status,
                "timestamp": result.timestamp
            }
            
            if result.status == "success":
                response_body.update({
                    "prediction": result.prediction,
                    "confidence": result.confidence,
                    "probabilities": result.probabilities,
                    "preprocessing": {
                        "pixel_min": result.preprocessing.pixel_min if result.preprocessing else 0.0,
                        "pixel_max": result.preprocessing.pixel_max if result.preprocessing else 0.0,
                        "pixel_mean": result.preprocessing.pixel_mean if result.preprocessing else 0.0,
                        "normalization_applied": result.preprocessing.normalization_applied if result.preprocessing else False,
                        "validation_passed": result.preprocessing.validation_passed if result.preprocessing else False,
                        "processing_time_ms": result.preprocessing.processing_time_ms if result.preprocessing else 0.0
                    },
                    "latency_ms": round(result.latency_ms, 1)
                })
                return MockAPIResponse(status_code=200, body=response_body)
            else:
                response_body.update({
                    "error_code": result.error_code or "UNKNOWN_ERROR",
                    "error_message": result.error_message,
                    "retry_count": result.retry_count
                })
                
                # Map error codes to HTTP status codes
                status_code_map: Dict[str, int] = {
                    "INVALID_REQUEST": 400,
                    "FILE_NOT_FOUND": 404,
                    "INVALID_IMAGE_FORMAT": 400,
                    "TIMEOUT": 408,
                    "CIRCUIT_BREAKER_OPEN": 503,
                    "MAX_RETRIES_EXCEEDED": 500
                }
                status_code = status_code_map.get(result.error_code or "UNKNOWN_ERROR", 500)
                
                return MockAPIResponse(status_code=status_code, body=response_body)
        
        except Exception as e:
            request_id_val: str = request_body.get("request_id", f"req_{uuid.uuid4()}")
            return self._error_response(
                status_code=500,
                error_code="INTERNAL_ERROR",
                error_message=str(e),
                request_id=request_id_val
            )
    
    def _error_response(self, status_code: int, error_code: str, 
                       error_message: str, request_id: Optional[str] = None) -> MockAPIResponse:
        """Build error response."""
        if not request_id:
            request_id = f"req_{uuid.uuid4()}"
        
        timestamp = datetime.now(timezone.utc).isoformat(timespec='microseconds')
        
        return MockAPIResponse(
            status_code=status_code,
            body={
                "request_id": request_id,
                "status": "failed",
                "error_code": error_code,
                "error_message": error_message,
                "timestamp": timestamp
            }
        )
    
    def health_check(self) -> MockAPIResponse:
        """GET /api/v2/health"""
        return MockAPIResponse(
            status_code=200,
            body={
                "status": "healthy",
                "version": "2.0.0",
                "circuit_breaker": self.classifier.circuit_breaker.get_state()
            }
        )
    
    def metrics(self) -> MockAPIResponse:
        """GET /api/v2/metrics"""
        audit_entries = self.classifier.audit_store.get_all()
        
        total_predictions = len(audit_entries)
        successful = sum(1 for e in audit_entries if e.status == "success")
        failed = total_predictions - successful
        
        latencies = [e.latency_ms for e in audit_entries]
        retry_counts = [e.retry_count for e in audit_entries]
        
        return MockAPIResponse(
            status_code=200,
            body={
                "total_predictions": total_predictions,
                "successful": successful,
                "failed": failed,
                "success_rate": successful / total_predictions if total_predictions > 0 else 0,
                "latency_stats": {
                    "min": min(latencies) if latencies else 0,
                    "max": max(latencies) if latencies else 0,
                    "mean": sum(latencies) / len(latencies) if latencies else 0,
                    "median": sorted(latencies)[len(latencies)//2] if latencies else 0
                },
                "retry_stats": {
                    "total_retries": sum(retry_counts),
                    "avg_retries_per_request": sum(retry_counts) / total_predictions if total_predictions > 0 else 0
                }
            }
        )


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    # Initialize mock API
    api = MockMNISTAPI('models/mnist_model.npy')
    
    # Example 1: Successful prediction
    print("=" * 60)
    print("Example 1: Successful Prediction")
    print("=" * 60)
    
    request_body = {
        "request_id": "req_example_001",
        "image_path": "data/test_digit_7.png",
        "timeout_ms": 5000,
        "retry_policy": {
            "max_retries": 3,
            "backoff_ms": [100, 200, 400]
        }
    }
    
    response = api.predict(request_body)
    print(f"Status Code: {response.status_code}")
    print(f"Response:\n{response.to_json()}")
    
    # Example 2: Idempotent request (should return cached result)
    print("\n" + "=" * 60)
    print("Example 2: Idempotent Request (Cache Hit)")
    print("=" * 60)
    
    response = api.predict(request_body)  # Same request_id
    print(f"Status Code: {response.status_code}")
    print(f"Response:\n{response.to_json()}")
    
    # Example 3: Error case (file not found)
    print("\n" + "=" * 60)
    print("Example 3: Error Case (File Not Found)")
    print("=" * 60)
    
    error_request = {
        "request_id": "req_example_002",
        "image_path": "data/nonexistent.png"
    }
    
    response = api.predict(error_request)
    print(f"Status Code: {response.status_code}")
    print(f"Response:\n{response.to_json()}")
    
    # Example 4: Health check
    print("\n" + "=" * 60)
    print("Example 4: Health Check")
    print("=" * 60)
    
    response = api.health_check()
    print(f"Status Code: {response.status_code}")
    print(f"Response:\n{response.to_json()}")
    
    # Example 5: Metrics
    print("\n" + "=" * 60)
    print("Example 5: Metrics")
    print("=" * 60)
    
    response = api.metrics()
    print(f"Status Code: {response.status_code}")
    print(f"Response:\n{response.to_json()}")

