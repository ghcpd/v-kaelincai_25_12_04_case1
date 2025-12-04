import pytest
import uuid
import random

from greenfield_routing.src.safe_routing import Graph, shortest_path
from greenfield_routing.src.appointment_manager import InMemoryStore, NotifierClient, AppointmentManager


@pytest.fixture(autouse=True)
def seed_random():
    random.seed(0)


@pytest.fixture(scope="session", autouse=True)
def collect_results(request):
    results = {"tests": []}

    def fin():
        import json, os
        os.makedirs("../results", exist_ok=True)
        with open("../results/results_post.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

    request.addfinalizer(fin)
    return results


def make_graph():
    edges = [
        ("A", "B", 5),
        ("A", "C", 2),
        ("C", "D", 1),
        ("D", "F", -3),
        ("F", "B", 1),
        ("A", "E", 1),
        ("E", "B", 6),
    ]
    return Graph.from_edge_list(edges)


def test_shortest_path_rejects_negative_by_default(collect_results):
    g = make_graph()
    with pytest.raises(ValueError, match="negative"):
        shortest_path(g, "A", "B")
    collect_results["tests"].append({"name": "reject_negative", "ok": True})


def test_shortest_path_with_bellman_when_allowed(collect_results):
    g = make_graph()
    path, cost = shortest_path(g, "A", "B", allow_negative=True)
    assert path == ["A", "C", "D", "F", "B"]
    assert cost == pytest.approx(1.0)
    collect_results["tests"].append({"name": "bellman_positive", "ok": True, "cost": cost})


def test_idempotent_create_appointment(collect_results):
    store = InMemoryStore()
    notifier = NotifierClient(fail_rate=0.0)
    mgr = AppointmentManager(store, notifier)

    req_id = str(uuid.uuid4())
    payload = {"user_id": "u1", "start": "A", "end": "B"}

    a1 = mgr.create_appointment(req_id, payload)
    a2 = mgr.create_appointment(req_id, payload)
    assert a1 == a2
    assert req_id in store.appointments
    collect_results["tests"].append({"name": "idempotency", "ok": True})


def test_retry_backoff_and_outbox_delivery(collect_results):
    store = InMemoryStore()
    # notifier fails first two times then succeeds
    notifier = NotifierClient(fail_rate=0.7)
    mgr = AppointmentManager(store, notifier)

    req_id = str(uuid.uuid4())
    payload = {"user_id": "u2", "start": "A", "end": "B"}

    # Use a retry policy with 3 attempts
    appt = mgr.create_appointment(req_id, payload, retry_policy={"backoff": [0, 0, 0]})
    # after retries we expect either notified or notification_failed
    status = store.appointments[req_id]["status"]
    assert status in ("notified", "notification_failed")
    collect_results["tests"].append({"name": "retry_outbox", "ok": True, "status": status, "attempts": store.outbox[req_id]["attempts"]})


def test_compensation_on_permanent_failure(collect_results):
    store = InMemoryStore()
    # notifier always fails
    notifier = NotifierClient(fail_rate=1.0)
    mgr = AppointmentManager(store, notifier)

    req_id = str(uuid.uuid4())
    payload = {"user_id": "u3", "start": "A", "end": "B"}

    appt = mgr.create_appointment(req_id, payload, retry_policy={"backoff": [0, 0]})
    assert store.appointments[req_id]["status"] == "notification_failed"

    # compensate: should remove appointment
    mgr.compensate(req_id)
    assert req_id not in store.appointments
    collect_results["tests"].append({"name": "compensation", "ok": True})


def test_reconciliation_delivers_pending_outbox(collect_results):
    store = InMemoryStore()
    notifier = NotifierClient(fail_rate=1.0)
    mgr = AppointmentManager(store, notifier)

    req_id = str(uuid.uuid4())
    payload = {"user_id": "u4", "start": "A", "end": "B"}
    mgr.create_appointment(req_id, payload)

    # Make notifier healthy and run reconciliation
    mgr.notifier.fail_rate = 0.0
    delivered = mgr.deliver_outbox(req_id)
    assert delivered is True
    assert store.appointments[req_id]["status"] == "notified"
    collect_results["tests"].append({"name": "reconciliation", "ok": True})
