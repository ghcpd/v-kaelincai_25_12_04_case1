from __future__ import annotations

import time
from typing import Optional


class CircuitBreakerOpen(Exception):
    pass


class CircuitBreaker:
    """Minimal sliding-window circuit breaker."""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = "closed"  # closed | open | half_open
        self.failure_count = 0
        self.last_opened: Optional[float] = None

    def _can_attempt(self) -> bool:
        if self.state == "open":
            assert self.last_opened is not None
            if (time.time() - self.last_opened) >= self.recovery_timeout:
                # Transition to half-open
                self.state = "half_open"
                return True
            return False
        return True

    def call(self, fn, *args, **kwargs):
        if not self._can_attempt():
            raise CircuitBreakerOpen()
        try:
            result = fn(*args, **kwargs)
        except Exception:
            self.record_failure()
            raise
        else:
            self.record_success()
            return result

    def record_success(self):
        # Close breaker on success
        self.failure_count = 0
        self.state = "closed"
        self.last_opened = None

    def record_failure(self):
        self.failure_count += 1
        if self.state == "half_open":
            # Any failure in half-open re-opens
            self._open()
        elif self.failure_count >= self.failure_threshold:
            self._open()

    def _open(self):
        self.state = "open"
        self.last_opened = time.time()