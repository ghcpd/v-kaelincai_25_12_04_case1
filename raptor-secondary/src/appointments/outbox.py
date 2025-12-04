from __future__ import annotations

from typing import List
from threading import Lock
from appointments.models import OutboxEvent


class InMemoryOutbox:
    def __init__(self) -> None:
        self._events: List[OutboxEvent] = []
        self._lock = Lock()

    def add(self, event: OutboxEvent) -> None:
        with self._lock:
            self._events.append(event)

    def get_pending(self) -> List[OutboxEvent]:
        with self._lock:
            return [e for e in self._events if not e.dispatched]

    def mark_dispatched(self, event_id: str) -> None:
        with self._lock:
            for e in self._events:
                if e.id == event_id:
                    e.dispatched = True

    def all(self) -> List[OutboxEvent]:
        with self._lock:
            return list(self._events)

    def clear(self):
        with self._lock:
            self._events.clear()
