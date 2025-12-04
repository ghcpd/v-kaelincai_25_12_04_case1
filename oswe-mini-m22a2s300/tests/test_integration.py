import json
import time
import pytest
from pathlib import Path
from typing import Dict

from src import algorithms

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "graph_negative_weight.json"


def load_graph(path: Path) -> Dict[str, Dict[str, float]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    g = {}
    for e in data["edges"]:
        g.setdefault(e["source"], {})[e["target"]] = e["weight"]
        g.setdefault(e["target"], {})
    return g


def test_healthy_non_negative_path():
    # graph without negative edges
    graph = {"A": {"B": 5, "C": 2}, "C": {"B": 2}, "B": {}}
    path, cost, algo = algorithms.compute_shortest_path(graph, "A", "B")
    assert path == ["A", "C", "B"]
    assert algo == "dijkstra"


def test_reject_negative_by_default():
    graph = load_graph(FIXTURE)
    with pytest.raises(ValueError, match="negative"):
        algorithms.compute_shortest_path(graph, "A", "B")


def test_bellman_handles_negative_when_allowed():
    graph = load_graph(FIXTURE)
    path, cost, algo = algorithms.compute_shortest_path(graph, "A", "B", allow_negative=True)
    assert path == ["A", "C", "D", "F", "B"]
    assert algo == "bellman-ford"
    assert cost == pytest.approx(1.0)


def test_idempotency_simulation():
    # Simple in-memory idempotency store
    store = {}
    def process(req_id: str, key: str):
        if key in store:
            return store[key]
        # simulate side-effect
        result = {"status": "ok", "req_id": req_id}
        store[key] = result
        return result

    r1 = process("r1", "k1")
    r2 = process("r1", "k1")
    assert r1 is r2


def test_retry_with_backoff_simulation():
    attempt = {"n": 0}
    def flaky():
        attempt["n"] += 1
        if attempt["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    # simple retry
    start = time.time()
    max_attempts = 5
    delay = 0.01
    for i in range(max_attempts):
        try:
            res = flaky()
            break
        except RuntimeError:
            time.sleep(delay * (2 ** i))
    else:
        pytest.fail("flaky never succeeded")
    assert res == "ok"
    assert attempt["n"] == 3


def test_timeout_and_circuit_breaker_simulation():
    # Simulate external call that times out and a simple circuit breaker
    def external_call(delay_sec: float):
        time.sleep(delay_sec)
        return "ok"

    timeout = 0.05
    def call_with_timeout(delay):
        start = time.time()
        res = external_call(delay)
        elapsed = time.time() - start
        if elapsed > timeout:
            raise TimeoutError("timeout")
        return res

    with pytest.raises(TimeoutError):
        call_with_timeout(0.1)

    # Simple CB: open after 2 failures
    cb = {"failures": 0, "open": False}
    for _ in range(2):
        try:
            call_with_timeout(0.1)
        except TimeoutError:
            cb["failures"] += 1
    if cb["failures"] >= 2:
        cb["open"] = True
    assert cb["open"]


def test_compensation_outbox_simulation(tmp_path):
    # Simulate saga with outbox and compensation
    state = {"booking": "pending"}
    outbox = []
    def step_reserve():
        # reserve resource
        state["booking"] = "reserved"
        outbox.append({"type": "reserve", "id": 1})
    def step_notify():
        # fail to notify
        raise RuntimeError("notify failed")
    def compensate():
        state["booking"] = "cancelled"
        outbox.append({"type": "compensate", "id": 1})

    step_reserve()
    try:
        step_notify()
    except RuntimeError:
        compensate()

    assert state["booking"] == "cancelled"
    assert any(ev["type"] == "compensate" for ev in outbox)


# Observability assertion placeholder: tests would assert logs/metrics in prod harness
