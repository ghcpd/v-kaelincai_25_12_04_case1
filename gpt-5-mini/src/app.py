import time
import threading
import uuid
import json
from typing import Dict, Any, Optional

# Simple in-memory stores for demo purposes
APPOINTMENTS: Dict[str, Dict[str, Any]] = {}
OUTBOX: Dict[str, Dict[str, Any]] = {}
IDEMPOTENCY_KEYS: Dict[str, str] = {}


class CircuitBreaker:
    def __init__(self, fail_threshold=3, reset_timeout=5):
        self.fail_threshold = fail_threshold
        self.reset_timeout = reset_timeout
        self.fail_count = 0
        self.open_until = 0

    def allow(self):
        if time.time() < self.open_until:
            return False
        return True

    def record_success(self):
        self.fail_count = 0

    def record_failure(self):
        self.fail_count += 1
        if self.fail_count >= self.fail_threshold:
            self.open_until = time.time() + self.reset_timeout


CB = CircuitBreaker()


def retry_with_backoff(fn, tries=3, base_delay=0.1, max_delay=1.0, timeout=None):
    start = time.time()
    for attempt in range(1, tries + 1):
        try:
            return fn()
        except Exception as e:
            if timeout and (time.time() - start) > timeout:
                raise
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            time.sleep(delay)
    raise RuntimeError('Retries exhausted')


def send_outbox(entry_id: str):
    entry = OUTBOX.get(entry_id)
    if not entry:
        return False
    # Here we would call external services; for demo we just mark sent
    entry['sent_at'] = time.time()
    entry['status'] = 'sent'
    return True


def create_appointment(payload: Dict[str, Any], idempotency_key: Optional[str] = None) -> Dict[str, Any]:
    # idempotency
    if idempotency_key and idempotency_key in IDEMPOTENCY_KEYS:
        appt_id = IDEMPOTENCY_KEYS[idempotency_key]
        return APPOINTMENTS[appt_id]

    if not CB.allow():
        raise RuntimeError('Circuit open')

    appt_id = str(uuid.uuid4())
    appt = {
        'id': appt_id,
        'status': 'init',
        'payload': payload,
        'created_at': time.time(),
        'events': []
    }
    APPOINTMENTS[appt_id] = appt
    if idempotency_key:
        IDEMPOTENCY_KEYS[idempotency_key] = appt_id

    # Enqueue outbox message to notify downstream
    out_id = str(uuid.uuid4())
    OUTBOX[out_id] = {'id': out_id, 'appt_id': appt_id, 'payload': {'action': 'create', 'appt': appt}, 'status': 'pending'}

    # try to send with retries
    try:
        def attempt():
            # simulate external call (replace with real HTTP client)
            send_outbox(out_id)
            return True
        retry_with_backoff(attempt, tries=3, base_delay=0.1)
        appt['status'] = 'scheduled'
        appt['events'].append({'t': time.time(), 'e': 'scheduled'})
        CB.record_success()
    except Exception:
        appt['status'] = 'pending_notification'
        appt['events'].append({'t': time.time(), 'e': 'notification_failed'})
        CB.record_failure()

    return appt


def cancel_appointment(appt_id: str) -> Dict[str, Any]:
    appt = APPOINTMENTS.get(appt_id)
    if not appt:
        raise KeyError('not found')
    if appt['status'] in ('cancelled', 'failed'):
        return appt
    appt['status'] = 'cancelled'
    appt['events'].append({'t': time.time(), 'e': 'cancelled'})
    return appt


def reconcile_outbox():
    for oid, entry in list(OUTBOX.items()):
        if entry['status'] != 'sent':
            try:
                send_outbox(oid)
            except Exception:
                pass


if __name__ == '__main__':
    print('Module loaded as script for quick manual tests')
