import pytest

from appointments import service


def setup_function(fn):
    service.clear_state()


def test_create_is_idempotent():
    payload = {"when": "2025-12-04T10:00:00Z", "user": "alice"}
    r1 = service.create_or_get_appointment("req-1", payload)
    r2 = service.create_or_get_appointment("req-1", payload)
    assert r1 is r2
    assert r1["state"] == service.AppointmentState.NEW
    outbox = service.get_outbox()
    assert "req-1" in outbox
