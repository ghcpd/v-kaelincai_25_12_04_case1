from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional
import uuid


class Status(Enum):
    INIT = 'init'
    SCHEDULED = 'scheduled'
    CONFIRMED = 'confirmed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


@dataclass
class Appointment:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    payload: Dict = field(default_factory=dict)
    status: Status = Status.INIT
    attempts: int = 0
    idempotency_key: Optional[str] = None


class AppointmentStore:
    """In-memory store for prototypes. In production this would be a durable DB."""

    def __init__(self):
        self._store: Dict[str, Appointment] = {}

    def upsert(self, appt: Appointment):
        self._store[appt.id] = appt

    def get(self, id: str) -> Optional[Appointment]:
        return self._store.get(id)

    def find_by_idempotency(self, key: str) -> Optional[Appointment]:
        for a in self._store.values():
            if a.idempotency_key == key:
                return a
        return None
