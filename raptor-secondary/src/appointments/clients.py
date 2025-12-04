from __future__ import annotations

from typing import Any
from appointments.models import RouteRequest, RouteResponse, AppointmentCreateRequest
from appointments.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from appointments.retry_policy import default_retry


class RoutingClient:
    def __init__(self, backend, breaker: CircuitBreaker, timeout: float = 0.5):
        self.backend = backend
        self.breaker = breaker
        self.timeout = timeout

    @default_retry(Exception, attempts=3)
    def route(self, req: RouteRequest) -> RouteResponse:
        def call_backend():
            import time
            start = time.time()
            result = self.backend.route(req)
            duration = time.time() - start
            if duration > self.timeout:
                raise TimeoutError(f"routing timeout after {duration:.3f}s")
            return result

        return self.breaker.call(call_backend)


class BookingClient:
    def __init__(self, backend, breaker: CircuitBreaker, timeout: float = 1.0):
        self.backend = backend
        self.breaker = breaker
        self.timeout = timeout

    @default_retry(Exception, attempts=3)
    def book(self, req: AppointmentCreateRequest) -> Any:
        def call_backend():
            import time
            start = time.time()
            result = self.backend.book(req)
            duration = time.time() - start
            if duration > self.timeout:
                raise TimeoutError(f"booking timeout after {duration:.3f}s")
            return result

        return self.breaker.call(call_backend)
