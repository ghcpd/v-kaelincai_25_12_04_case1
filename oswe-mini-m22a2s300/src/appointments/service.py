from __future__ import annotations

from typing import Dict, Any, Optional
import time

# Simple in-memory store to simulate DB
_APPOINTMENTS: Dict[str, Dict[str, Any]] = {}
_OUTBOX: Dict[str, Any] = {}

class AppointmentState:
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


def create_or_get_appointment(request_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Idempotent create: if request_id exists, return existing record."""
    if request_id in _APPOINTMENTS:
        return _APPOINTMENTS[request_id]
    record = {
        "request_id": request_id,
        "payload": payload,
        "state": AppointmentState.NEW,
        "created_at": time.time(),
    }
    _APPOINTMENTS[request_id] = record
    # Simulate transactional outbox write
    _OUTBOX[request_id] = {"event": "appointment.created", "data": record}
    return record


def transition_state(request_id: str, to_state: str) -> Dict[str, Any]:
    rec = _APPOINTMENTS.get(request_id)
    if not rec:
        raise KeyError("unknown request_id")
    rec["state"] = to_state
    return rec


def clear_state():
    _APPOINTMENTS.clear()
    _OUTBOX.clear()
    # Reset circuit breaker for test isolation and clean start
    _CIRCUIT["consecutive_failures"] = 0
    _CIRCUIT["open"] = False


def get_outbox():
    return dict(_OUTBOX)


# Simple circuit-breaker and retry/outbox processing utilities
_CIRCUIT = {"consecutive_failures": 0, "open": False}


def _record_failure():
    _CIRCUIT["consecutive_failures"] += 1
    if _CIRCUIT["consecutive_failures"] >= 3:
        _CIRCUIT["open"] = True


def _record_success():
    _CIRCUIT["consecutive_failures"] = 0
    _CIRCUIT["open"] = False


def process_outbox_with(handler, *, max_retries: int = 3, backoff_base: float = 0.1, timeout: Optional[float] = None):
    """Attempt to deliver all outbox events using handler(payload).

    Handler should raise exceptions on failure. On success, handler returns a dict response.
    Retries are attempted with exponential backoff. If circuit is open, raises RuntimeError.
    """
    if _CIRCUIT["open"]:
        raise RuntimeError("circuit open")

    # Process a snapshot to avoid mutation during iteration
    for req_id, ev in list(_OUTBOX.items()):
        rec = _APPOINTMENTS.get(req_id)
        attempts = 0
        while attempts <= max_retries:
            try:
                # In a real system apply a timeout wrapper; here we simulate by catching TimeoutError
                res = handler(ev["data"]["payload"])
                # On success, mark appointment completed and remove outbox
                rec["state"] = AppointmentState.COMPLETED
                _OUTBOX.pop(req_id, None)
                _record_success()
                break
            except TimeoutError:
                # Treat timeouts as severe: immediately open the circuit and fail fast
                _CIRCUIT["consecutive_failures"] = 3
                _CIRCUIT["open"] = True
                rec["state"] = AppointmentState.FAILED
                raise RuntimeError("circuit open")
            except Exception:
                attempts += 1
                _record_failure()
                if attempts > max_retries:
                    rec["state"] = AppointmentState.FAILED
                    break
                # backoff
                time.sleep(backoff_base * (2 ** (attempts - 1)))


def reconcile_outbox(handler, *, max_retries: int = 3, backoff_base: float = 0.1):
    """Background reconciliation that tries to deliver outstanding outbox events."""
    process_outbox_with(handler, max_retries=max_retries, backoff_base=backoff_base)


def simulate_outbox_process_with_db_failure_then_compensate(req_id: str, handler, mocks_module):
    """Simulate the case where external call succeeds but DB commit fails, requiring compensation."""
    ev = _OUTBOX.get(req_id)
    if not ev:
        raise KeyError("no outbox event")
    rec = _APPOINTMENTS.get(req_id)
    try:
        res = handler(ev["data"]["payload"])
        # Simulate DB write failure
        raise RuntimeError("db commit failed")
    except Exception:
        # Compensation: call external cancel if available
        if hasattr(mocks_module, "cancel_calendar_event"):
            try:
                mocks_module.cancel_calendar_event(ev["data"]["payload"])  # best-effort
            except Exception:
                pass
        rec["state"] = AppointmentState.CANCELLED
        _OUTBOX.pop(req_id, None)
