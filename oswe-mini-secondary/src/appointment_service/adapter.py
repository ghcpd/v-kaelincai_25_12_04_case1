import time
from typing import Callable

class TransientError(Exception):
    pass

class PermanentError(Exception):
    pass


class CircuitBreaker:
    def __init__(self, fail_threshold: int = 3, reset_timeout: float = 30.0):
        self.fail_threshold = fail_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.opened_at = None

    def allow(self) -> bool:
        if self.opened_at is None:
            return True
        if time.time() - self.opened_at > self.reset_timeout:
            # reset
            self.failure_count = 0
            self.opened_at = None
            return True
        return False

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.fail_threshold:
            self.opened_at = time.time()

    def record_success(self) -> None:
        self.failure_count = 0
        self.opened_at = None


class CalendarAdapter:
    def __init__(self, call_fn: Callable[[dict], dict], circuit_breaker: CircuitBreaker | None = None, timeout: float = 1.5):
        self._fn = call_fn
        self.circuit = circuit_breaker or CircuitBreaker()
        self.timeout = timeout

    def schedule(self, payload: dict) -> dict:
        if not self.circuit.allow():
            raise TransientError("circuit-open")

        start = time.time()
        try:
            # simulate timeout by checkpointing timeouts inside the mock
            res = self._fn(payload)
            duration = time.time() - start
            if duration > self.timeout:
                raise TransientError("timeout")
            self.circuit.record_success()
            return res
        except TransientError:
            self.circuit.record_failure()
            raise
        except PermanentError:
            self.circuit.record_failure()
            raise
        except Exception:
            self.circuit.record_failure()
            # treat unknown as transient for this prototype
            raise TransientError("unknown")
