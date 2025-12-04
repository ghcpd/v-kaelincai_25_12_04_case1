import time
import random
from typing import Dict, Any, Optional


class InMemoryStore:
    def __init__(self):
        self.appointments: Dict[str, Dict[str, Any]] = {}
        self.outbox: Dict[str, Dict[str, Any]] = {}


class NotifierClient:
    def __init__(self, endpoint=None, fail_rate=0.0, delay=0.0):
        self.endpoint = endpoint
        self.fail_rate = fail_rate
        self.delay = delay
        self.failure_count = 0

    def send(self, payload: Dict[str, Any]):
        # Simulate delay
        if self.delay > 0:
            time.sleep(self.delay)
        # Simulate transient failure
        if random.random() < self.fail_rate:
            self.failure_count += 1
            raise ConnectionError("transient notifier failure")
        return {"status": "ok"}


class AppointmentManager:
    def __init__(self, store: InMemoryStore, notifier: NotifierClient):
        self.store = store
        self.notifier = notifier

    def create_appointment(self, request_id: str, payload: Dict[str, Any], retry_policy=None):
        # Idempotency: if request_id exists return existing
        if request_id in self.store.appointments:
            return self.store.appointments[request_id]

        # Persist appointment (primary write)
        appt = dict(payload)
        appt["status"] = "created"
        self.store.appointments[request_id] = appt

        # Write an outbox event
        event = {"request_id": request_id, "payload": payload, "sent": False, "attempts": 0}
        self.store.outbox[request_id] = event

        # Attempt to deliver immediately with retries if provided
        if retry_policy:
            return self._deliver_with_retry(request_id, retry_policy)
        else:
            return appt

    def _deliver_with_retry(self, request_id: str, retry_policy: Dict[str, Any]):
        backoff = retry_policy.get("backoff", [0.1, 0.2, 0.5])
        for attempt, delay in enumerate(backoff, start=1):
            try:
                self.store.outbox[request_id]["attempts"] = attempt
                self.notifier.send(self.store.outbox[request_id]["payload"])
                self.store.outbox[request_id]["sent"] = True
                self.store.appointments[request_id]["status"] = "notified"
                return self.store.appointments[request_id]
            except Exception as e:
                time.sleep(delay)
                continue
        # final failed state
        self.store.appointments[request_id]["status"] = "notification_failed"
        return self.store.appointments[request_id]

    def deliver_outbox(self, request_id: str):
        event = self.store.outbox.get(request_id)
        if not event:
            return False
        try:
            self.notifier.send(event["payload"])
            event["sent"] = True
            self.store.appointments[request_id]["status"] = "notified"
            return True
        except Exception:
            event["attempts"] += 1
            return False

    def compensate(self, request_id: str):
        # Example compensation: delete appointment and outbox
        if request_id in self.store.appointments:
            del self.store.appointments[request_id]
        if request_id in self.store.outbox:
            del self.store.outbox[request_id]
        return True
