import json
from pathlib import Path

import pytest

from appointments.models import AppointmentCreateRequest, Location, Constraints, AppointmentState
from appointments.service import reconcile_outbox

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "test_data.json"


@pytest.fixture(scope="module")
def test_cases():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return {case["name"]: case for case in json.load(f)}


def make_request(case):
    return AppointmentCreateRequest(
        idempotency_key=case["idempotency_key"],
        customer_id="cust-1",
        requested_time="2025-12-04T10:00:00Z",
        location=Location(lat=40.0, lng=-74.0),
        constraints=Constraints(),
        metadata={
            "edges": case["edges"],
            "source": case["source"],
            "target": case["target"],
        },
    )


def test_healthy_path(service, backend, test_cases, record_metrics):
    case = test_cases["healthy_path"]
    backend.scenario_by_key[case["idempotency_key"]] = case["scenario"]
    req = make_request(case)

    import time
    start = time.perf_counter()
    resp = service.create_appointment(req)
    duration_ms = (time.perf_counter() - start) * 1000

    assert resp.state == AppointmentState.CONFIRMED
    assert resp.route_path == ["A", "C", "D", "F", "B"]
    assert resp.route_cost == pytest.approx(1.0)
    assert len(service.outbox.all()) == 1
    record_metrics(duration_ms=duration_ms, retries_routing=backend.route_calls.get(case["idempotency_key"], 0) - 1, retries_booking=backend.booking_calls.get(case["idempotency_key"], 0) - 1)


def test_idempotent_duplicate(service, backend, test_cases, record_metrics):
    case = test_cases["idempotent_duplicate"]
    backend.scenario_by_key[case["idempotency_key"]] = case["scenario"]
    req = make_request(case)

    import time
    start = time.perf_counter(); resp1 = service.create_appointment(req); t1 = time.perf_counter()
    resp2 = service.create_appointment(req); t2 = time.perf_counter()
    duration_ms = (t2 - start) * 1000

    assert resp1.state == AppointmentState.CONFIRMED
    assert resp2.repeated is True
    assert backend.booking_calls[case["idempotency_key"]] == 1
    record_metrics(duration_ms=duration_ms, repeated=True)


def test_routing_timeout_breaker(service, backend, test_cases, record_metrics):
    case = test_cases["routing_timeout_breaker"]
    backend.scenario_by_key[case["idempotency_key"]] = case["scenario"]
    req = make_request(case)

    import time
    start = time.perf_counter()
    resp = service.create_appointment(req)
    duration_ms = (time.perf_counter() - start) * 1000

    assert resp.state == AppointmentState.FAILED
    # Breaker should be open after repeated timeouts
    assert service.routing_client.breaker.state in {"open", "half_open"}
    assert backend.route_calls[case["idempotency_key"]] >= 1
    record_metrics(duration_ms=duration_ms, breaker_state=service.routing_client.breaker.state)


def test_booking_fail_once(service, backend, test_cases, record_metrics):
    case = test_cases["booking_fail_once"]
    backend.scenario_by_key[case["idempotency_key"]] = case["scenario"]
    req = make_request(case)

    import time
    start = time.perf_counter()
    resp = service.create_appointment(req)
    duration_ms = (time.perf_counter() - start) * 1000

    assert resp.state == AppointmentState.CONFIRMED
    assert backend.booking_calls[case["idempotency_key"]] == 2  # retried once
    record_metrics(duration_ms=duration_ms, retries_booking=1)


def test_audit_reconcile(service, backend, test_cases, record_metrics):
    case = test_cases["audit_reconcile"]
    backend.scenario_by_key[case["idempotency_key"]] = case["scenario"]
    req = make_request(case)

    import time
    start = time.perf_counter()
    _ = service.create_appointment(req)
    duration_ms = (time.perf_counter() - start) * 1000

    dispatched = []

    def dispatcher(ev):
        dispatched.append(ev.id)

    count = reconcile_outbox(service.outbox, dispatcher)

    assert count >= 1
    assert len(dispatched) == count
    assert len(service.outbox.get_pending()) == 0
    record_metrics(duration_ms=duration_ms, outbox_dispatched=count)
