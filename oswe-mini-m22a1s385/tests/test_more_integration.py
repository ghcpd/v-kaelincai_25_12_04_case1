import time
from appointment import Appointment, AppointmentStore
from orchestrator import Orchestrator
from mocks.send_action_mock import FlakySender
from outbox import Outbox
from circuit_breaker import CircuitBreaker


def test_circuit_breaker_trips_and_recovers():
    cb = CircuitBreaker(failure_threshold=2, recovery_time=0.1)
    assert cb.allow()
    cb.record_failure()
    assert cb.allow()
    cb.record_failure()
    assert not cb.allow()
    time.sleep(0.11)
    assert cb.allow()


def test_outbox_compensation():
    out = Outbox()
    out.push({'type': 'notify', 'id': '1'})
    out.push({'type': 'write', 'id': '2'})
    items = out.pop_all()
    assert len(items) == 2
    assert out.pop_all() == []


def test_healthy_path_confirms():
    store = AppointmentStore()
    sender = FlakySender(0.0)
    orch = Orchestrator(store, sender)
    appt = Appointment()
    orch.schedule(appt, idempotency_key='ok')
    res = orch.confirm_with_retries(appt.id, max_attempts=1)
    assert res.status.name.lower() == 'confirmed'
