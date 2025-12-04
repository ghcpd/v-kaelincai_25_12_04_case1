import time
import json
import random

from pathlib import Path

import pytest

from routing_v2 import Graph, dijkstra_safe, bellman_ford
from appointment import Appointment, AppointmentStore
from orchestrator import Orchestrator
from mocks.send_action_mock import FlakySender


FIXTURE = Path(__file__).resolve().parents[1] / 'data' / 'test_data.json'


@pytest.fixture(autouse=True)
def seed_random():
    random.seed(0)


def load_graph(case):
    g = Graph()
    for a, b, w in case:
        g.add_edge(a, b, w)
    return g


def test_dijkstra_rejects_negative():
    data = json.load(open(FIXTURE))
    g = load_graph(data['cases'][0]['edges'])
    with pytest.raises(ValueError, match='negative'):
        dijkstra_safe(g, 'A', 'B')


def test_bellman_ford_handles_negative():
    data = json.load(open(FIXTURE))
    g = load_graph(data['cases'][0]['edges'])
    path, cost = bellman_ford(g, 'A', 'B')
    assert path[-1] == 'B'
    assert cost == pytest.approx(1.0)


def test_no_path_raises():
    data = json.load(open(FIXTURE))
    g = load_graph(data['cases'][2]['edges'])
    with pytest.raises(ValueError):
        bellman_ford(g, 'A', 'B')


def test_idempotent_schedule():
    store = AppointmentStore()
    orch = Orchestrator(store, FlakySender(0.0))
    appt = Appointment(payload={'when': '2025-12-04T10:00Z'})
    first = orch.schedule(appt, idempotency_key='abc')
    second = orch.schedule(Appointment(payload={'when': 'X'}), idempotency_key='abc')
    assert first.id == second.id


def test_retry_and_backoff_marks_final_status():
    store = AppointmentStore()
    sender = FlakySender(1.0)  # always fail
    orch = Orchestrator(store, sender)
    appt = Appointment(payload={})
    orch.schedule(appt, idempotency_key='retry-1')
    res = orch.confirm_with_retries(appt.id, max_attempts=3, backoff=0.01)
    assert res.status.name.lower() == 'failed'
