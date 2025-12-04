from __future__ import annotations

import time
from typing import Callable, Dict, Any

from appointment import Appointment, AppointmentStore, Status


class Orchestrator:
    def __init__(self, store: AppointmentStore, send_action: Callable[[Appointment], Dict[str, Any]]):
        self.store = store
        self.send_action = send_action

    def schedule(self, appt: Appointment, idempotency_key: str | None = None) -> Appointment:
        if idempotency_key:
            existing = self.store.find_by_idempotency(idempotency_key)
            if existing:
                return existing
            appt.idempotency_key = idempotency_key

        appt.status = Status.SCHEDULED
        self.store.upsert(appt)
        return appt

    def confirm_with_retries(self, appt_id: str, max_attempts: int = 3, backoff: float = 0.1):
        appt = self.store.get(appt_id)
        if not appt:
            raise ValueError('unknown appointment')

        for attempt in range(1, max_attempts + 1):
            appt.attempts = attempt
            try:
                resp = self.send_action(appt)
                if resp.get('ok'):
                    appt.status = Status.CONFIRMED
                    self.store.upsert(appt)
                    return appt
                else:
                    appt.status = Status.FAILED
            except Exception:
                appt.status = Status.FAILED

            self.store.upsert(appt)
            time.sleep(backoff * attempt)

        # Compensation / outbox could be emitted here
        return appt
