import time
import pytest

from appointments import service
from mocks import mock_api


def setup_function(fn):
    service.clear_state()


def test_healthy_path_creates_event_and_outbox_processed():
    payload = {"when": "2025-12-04T10:00:00Z", "user": "alice"}
    rec = service.create_or_get_appointment("req-healthy", payload)
    # process outbox
    service.process_outbox_with(mock_api.create_calendar_event)
    assert rec["state"] == service.AppointmentState.COMPLETED
    outbox = service.get_outbox()
    assert outbox == {}


def test_retry_with_backoff_on_transient_calendar_error():
    payload = {"when": "2025-12-04T11:00:00Z", "user": "bob"}
    rec = service.create_or_get_appointment("req-retry", payload)
    # Simulate transient failures: function will fail twice then succeed
    call_count = {"n": 0}
    def flaky(payload):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise RuntimeError("transient")
        return {"calendar_id": "cal-bob"}

    service.process_outbox_with(flaky, max_retries=4, backoff_base=0.01)
    assert rec["state"] == service.AppointmentState.COMPLETED
    assert call_count["n"] == 3


def test_timeout_and_circuit_breaker_marks_failed():
    payload = {"when": "2025-12-04T12:00:00Z", "user": "carol"}
    rec = service.create_or_get_appointment("req-cb", payload)

    def slow(payload):
        raise TimeoutError("timeout")

    with pytest.raises(RuntimeError, match="circuit open"):
        service.process_outbox_with(slow, max_retries=1, backoff_base=0.01, timeout=0.01)
    assert rec["state"] == service.AppointmentState.FAILED


def test_compensation_runs_on_partial_success():
    payload = {"when": "2025-12-04T13:00:00Z", "user": "dave"}
    rec = service.create_or_get_appointment("req-comp", payload)

    # Calendar created but DB commit fails; service should attempt compensation (cancel calendar)
    def create_then_db_fail(payload):
        # return calendar id
        return {"calendar_id": "cal-dave"}

    # Simulate process where after external success a DB write fails triggering compensation
    service.simulate_outbox_process_with_db_failure_then_compensate("req-comp", create_then_db_fail, mock_api)
    assert rec["state"] in (service.AppointmentState.FAILED, service.AppointmentState.CANCELLED)


def test_reconciliation_finds_and_delivers_outbox():
    payload = {"when": "2025-12-04T14:00:00Z", "user": "eve"}
    rec = service.create_or_get_appointment("req-recon", payload)
    # initially outbox contains event
    assert "req-recon" in service.get_outbox()
    # run background reconcile which should call calendar and clear outbox
    service.reconcile_outbox(mock_api.create_calendar_event)
    assert "req-recon" not in service.get_outbox()
    assert rec["state"] == service.AppointmentState.COMPLETED
