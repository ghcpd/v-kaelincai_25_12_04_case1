"""
Circuit breaker pattern for graceful degradation.
"""

from typing import Callable, TypeVar, Any
from enum import Enum
from collections import deque
from datetime import datetime, timedelta

T = TypeVar('T')


class CircuitBreakerState(Enum):
    """Circuit breaker state machine."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker for resilience.
    
    State machine:
      CLOSED → (failure rate > threshold) → OPEN
      OPEN → (timeout expires) → HALF_OPEN
      HALF_OPEN → (test request succeeds) → CLOSED
      HALF_OPEN → (test request fails) → OPEN
    """
    
    def __init__(
        self,
        failure_threshold: float = 0.5,
        recovery_timeout_seconds: int = 30,
        window_size: int = 100,
        min_requests_for_threshold: int = 10,
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Error rate threshold (0.0 - 1.0) to open circuit
            recovery_timeout_seconds: Wait before entering HALF_OPEN
            window_size: Number of recent requests to track (sliding window)
            min_requests_for_threshold: Minimum requests before evaluating threshold
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.window_size = window_size
        self.min_requests_for_threshold = min_requests_for_threshold
        
        self.state = CircuitBreakerState.CLOSED
        self.requests: deque = deque(maxlen=window_size)  # Track success/failure
        self.last_failure_time: datetime = datetime.utcnow()
        self.last_state_change: datetime = datetime.utcnow()
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Result of func(*args, **kwargs)
        
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Any exception raised by func
        """
        if self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout expired
            time_since_failure = datetime.utcnow() - self.last_failure_time
            if time_since_failure.total_seconds() >= self.recovery_timeout_seconds:
                self._transition_to(CircuitBreakerState.HALF_OPEN)
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is open; retry after "
                    f"{self.recovery_timeout_seconds - time_since_failure.total_seconds():.1f}s"
                )
        
        try:
            result = func(*args, **kwargs)
            self.requests.append("success")
            
            # Transition from HALF_OPEN to CLOSED on success
            if self.state == CircuitBreakerState.HALF_OPEN:
                self._transition_to(CircuitBreakerState.CLOSED)
            
            return result
        
        except Exception as e:
            self.requests.append("failure")
            self.last_failure_time = datetime.utcnow()
            
            # Evaluate failure rate
            if len(self.requests) >= self.min_requests_for_threshold:
                failure_rate = sum(1 for r in self.requests if r == "failure") / len(self.requests)
                if failure_rate > self.failure_threshold:
                    self._transition_to(CircuitBreakerState.OPEN)
            
            raise
    
    def _transition_to(self, new_state: CircuitBreakerState) -> None:
        """Transition to new state."""
        old_state = self.state
        self.state = new_state
        self.last_state_change = datetime.utcnow()
        # Note: Logging handled by caller
    
    def get_state(self) -> str:
        """Get current state."""
        return self.state.value
    
    def get_failure_rate(self) -> float:
        """Get current failure rate."""
        if not self.requests:
            return 0.0
        return sum(1 for r in self.requests if r == "failure") / len(self.requests)
    
    def stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            "state": self.state.value,
            "failure_rate": self.get_failure_rate(),
            "window_size": len(self.requests),
            "max_window_size": self.window_size,
            "last_state_change": self.last_state_change.isoformat(),
        }
    
    def reset(self) -> None:
        """Reset circuit breaker to CLOSED state."""
        self.state = CircuitBreakerState.CLOSED
        self.requests.clear()
        self.last_state_change = datetime.utcnow()
