from __future__ import annotations

import time


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_time: float = 5.0):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.failures = 0
        self.last_failure_time = 0.0

    def allow(self) -> bool:
        if self.failures < self.failure_threshold:
            return True
        if time.time() - self.last_failure_time > self.recovery_time:
            self.failures = 0
            return True
        return False

    def record_success(self):
        self.failures = 0

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
