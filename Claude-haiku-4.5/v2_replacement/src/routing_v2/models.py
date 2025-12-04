"""
Request/response models and error handling.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
from enum import Enum
import json


class ErrorCode(str, Enum):
    """Standard error codes."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NEGATIVE_WEIGHT_ERROR = "NEGATIVE_WEIGHT_ERROR"
    NOT_FOUND = "NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    CIRCUIT_BREAKER_OPEN = "CIRCUIT_BREAKER_OPEN"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class RouteRequest:
    """Route request."""
    request_id: str
    start: str
    goal: str
    graph_id: str = "default"
    timeout_ms: int = 200
    algorithm: str = "dijkstra"  # "dijkstra" or "bellman_ford"
    
    def validate(self) -> List[str]:
        """Validate request; return list of errors."""
        errors = []
        if not self.request_id or not isinstance(self.request_id, str):
            errors.append("request_id must be non-empty string")
        if len(self.request_id) > 256:
            errors.append("request_id exceeds 256 characters")
        if not self.start or not isinstance(self.start, str):
            errors.append("start must be non-empty string")
        if len(self.start) > 100:
            errors.append("start exceeds 100 characters")
        if not self.goal or not isinstance(self.goal, str):
            errors.append("goal must be non-empty string")
        if len(self.goal) > 100:
            errors.append("goal exceeds 100 characters")
        if self.timeout_ms < 100 or self.timeout_ms > 5000:
            errors.append("timeout_ms must be between 100 and 5000")
        if self.algorithm not in ("dijkstra", "bellman_ford"):
            errors.append("algorithm must be 'dijkstra' or 'bellman_ford'")
        return errors
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> RouteRequest:
        """Create from dictionary."""
        return cls(
            request_id=data["request_id"],
            start=data["start"],
            goal=data["goal"],
            graph_id=data.get("graph_id", "default"),
            timeout_ms=data.get("timeout_ms", 200),
            algorithm=data.get("algorithm", "dijkstra"),
        )


@dataclass
class RouteResponse:
    """Successful route response."""
    request_id: str
    path: List[str]
    total_cost: float
    computation_time_ms: float
    was_cached: bool = False
    timestamp: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "path": self.path,
            "total_cost": self.total_cost,
            "computation_time_ms": self.computation_time_ms,
            "was_cached": self.was_cached,
            "timestamp": self.timestamp,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class ErrorResponse:
    """Error response."""
    request_id: str
    error_code: ErrorCode
    error_message: str
    details: Optional[Dict] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result: Dict = {
            "request_id": self.request_id,
            "error_code": self.error_code.value,
            "error_message": self.error_message,
        }
        if self.details:
            result["details"] = self.details
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @staticmethod
    def validation_error(request_id: str, message: str, details: Optional[Dict] = None) -> ErrorResponse:
        """Create validation error."""
        return ErrorResponse(
            request_id=request_id,
            error_code=ErrorCode.VALIDATION_ERROR,
            error_message=message,
            details=details,
        )
    
    @staticmethod
    def negative_weight_error(request_id: str, negative_edges: List) -> ErrorResponse:
        """Create negative weight error."""
        return ErrorResponse(
            request_id=request_id,
            error_code=ErrorCode.NEGATIVE_WEIGHT_ERROR,
            error_message="Graph contains negative-weight edges; Dijkstra cannot proceed",
            details={"negative_edges": negative_edges},
        )
    
    @staticmethod
    def timeout_error(request_id: str, timeout_ms: int) -> ErrorResponse:
        """Create timeout error."""
        return ErrorResponse(
            request_id=request_id,
            error_code=ErrorCode.TIMEOUT,
            error_message=f"Routing algorithm exceeded {timeout_ms}ms timeout",
        )
    
    @staticmethod
    def circuit_breaker_error(request_id: str) -> ErrorResponse:
        """Create circuit breaker error."""
        return ErrorResponse(
            request_id=request_id,
            error_code=ErrorCode.CIRCUIT_BREAKER_OPEN,
            error_message="Service temporarily unavailable; circuit breaker is open. Retry after 30 seconds.",
        )
    
    @staticmethod
    def internal_error(request_id: str, message: str) -> ErrorResponse:
        """Create internal error."""
        return ErrorResponse(
            request_id=request_id,
            error_code=ErrorCode.INTERNAL_ERROR,
            error_message=message,
        )
