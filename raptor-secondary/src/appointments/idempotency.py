from __future__ import annotations

from typing import Dict, Optional
from threading import Lock


class InMemoryIdempotencyStore:
    """Simple thread-safe idempotency store."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._store: Dict[str, dict] = {}

    def get(self, key: str) -> Optional[dict]:
        with self._lock:
            return self._store.get(key)

    def put(self, key: str, value: dict) -> None:
        with self._lock:
            # Do not overwrite existing to preserve idempotency
            if key not in self._store:
                self._store[key] = value

    def clear(self):
        with self._lock:
            self._store.clear()
