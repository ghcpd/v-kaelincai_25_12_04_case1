import pytest

from appointment_service.db import SimpleDB
from appointment_service.adapter import CalendarAdapter, CircuitBreaker, TransientError
from appointment_service.service import AppointmentService
from appointment_service.outbox_worker import OutboxWorker
from mocks.calendar_mock import MockCalendar


def run_worker_until(db, adapter, max_cycles=10):
    worker = OutboxWorker(db, adapter, max_attempts=3, backoff_seconds=0.01)
    for _ in range(max_cycles):
        worker.run_once()


def test_healthy_path_schedules_immediately():
    db = SimpleDB()
    mock = MockCalendar([{"type": "ok"}])
    adapter = CalendarAdapter(mock.call)
    svc = AppointmentService(db, adapter)

    appt_id = svc.create_appointment("r1", "u1", "2025-12-04T10:00:00Z", "2025-12-04T11:00:00Z", {"title": "mtg"})

    appt = db.get_appointment(appt_id)
    assert appt is not None
    assert appt["status"] == "SCHEDULED"


def test_idempotency_duplicate_request_returns_same():
    db = SimpleDB()
    mock = MockCalendar([{"type": "ok"}])
    adapter = CalendarAdapter(mock.call)
    svc = AppointmentService(db, adapter)

    appt_id1 = svc.create_appointment("r2", "u2", "2025-12-04T12:00:00Z", "2025-12-04T12:30:00Z", {})
    appt_id2 = svc.create_appointment("r2", "u2", "2025-12-04T12:00:00Z", "2025-12-04T12:30:00Z", {})

    assert appt_id1 == appt_id2
    appt = db.get_appointment(appt_id1)
    assert appt["status"] == "SCHEDULED"


def test_transient_then_success_outbox_retries_and_succeeds():
    db = SimpleDB()
    # first attempt transient, second ok
    mock = MockCalendar([{"type": "transient"}, {"type": "ok"}])
    adapter = CalendarAdapter(mock.call)
    svc = AppointmentService(db, adapter)

    appt_id = svc.create_appointment("r3", "u3", "2025-12-04T13:00:00Z", "2025-12-04T13:30:00Z", {})

    # initial synchronous schedule will have raised transient; appointment still PENDING
    appt = db.get_appointment(appt_id)
    assert appt["status"] == "PENDING"

    # let worker retry and succeed
    run_worker_until(db, adapter, max_cycles=3)
    appt = db.get_appointment(appt_id)
    assert appt["status"] == "SCHEDULED"


def test_circuit_breaker_opens_and_fails_fast():
    db = SimpleDB()
    # all transient errors
    mock = MockCalendar([{"type": "transient"}, {"type": "transient"}, {"type": "transient"}, {"type": "transient"}])
    cb = CircuitBreaker(fail_threshold=2, reset_timeout=60)
    adapter = CalendarAdapter(mock.call, circuit_breaker=cb, timeout=0.15)
    svc = AppointmentService(db, adapter)

    # create several appointments to trip circuit
    appt_ids = []
    for i in range(3):
        appt_ids.append(svc.create_appointment(f"r_cb_{i}", f"u{i}", "2025-12-04T15:00:00Z", "2025-12-04T15:30:00Z", {}))

    # circuit should be open after failures
    assert not cb.allow()

    # next immediate call should raise (circuit-open) and not block
    with pytest.raises(TransientError):
        adapter.schedule({})


def test_permanent_failure_marks_failed_after_outbox_max():
    db = SimpleDB()
    # permanent error will cause outbox attempts to increment and then mark as failed
    # repeat permanent responses so outbox retries will not succeed
    mock = MockCalendar([{"type": "permanent"}] * 6)
    adapter = CalendarAdapter(mock.call)
    svc = AppointmentService(db, adapter)

    appt_id = svc.create_appointment("r_perm", "u_perm", "2025-12-04T16:00:00Z", "2025-12-04T16:30:00Z", {})

    # initial scheduling failed and left PENDING
    appt = db.get_appointment(appt_id)
    assert appt["status"] in ("PENDING", "FAILED")

    # run worker until it marks failed
    run_worker_until(db, adapter, max_cycles=5)

    appt = db.get_appointment(appt_id)
    assert appt["status"] == "FAILED"
