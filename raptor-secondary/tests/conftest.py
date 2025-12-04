import sys
from pathlib import Path

# Add src to sys.path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest
from appointments.service import AppointmentService
from appointments.clients import RoutingClient, BookingClient
from appointments.circuit_breaker import CircuitBreaker
from mocks.api_v2 import MockBackend
from tests import metrics
import statistics
import json


@pytest.fixture
def backend():
    return MockBackend()


@pytest.fixture
def service(backend):
    routing_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)
    booking_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)
    routing_client = RoutingClient(backend=backend, breaker=routing_breaker, timeout=0.5)
    booking_client = BookingClient(backend=backend, breaker=booking_breaker, timeout=1.0)
    return AppointmentService(routing_client=routing_client, booking_client=booking_client)


@pytest.fixture
def record_metrics(request):
    def _rec(**kwargs):
        metrics.record(request.node.name, **kwargs)
    return _rec


def pytest_sessionfinish(session, exitstatus):
    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    metrics.export(results_dir / "results_post.json")

    # Aggregated metrics (p50/p95 durations if present)
    data = metrics.all_data()
    durations = [v.get("duration_ms") for v in data.values() if v.get("duration_ms") is not None]
    agg = {}
    if durations:
        durations_sorted = sorted(durations)
        agg["p50_duration_ms"] = statistics.median(durations_sorted)
        # p95 approximation
        idx = int(0.95 * (len(durations_sorted) - 1))
        agg["p95_duration_ms"] = durations_sorted[idx]
    agg["test_count"] = len(data)
    agg_path = ROOT / "Shared" / "results" / "aggregated_metrics.json"
    agg_path.parent.mkdir(parents=True, exist_ok=True)
    with open(agg_path, "w", encoding="utf-8") as f:
        json.dump(agg, f, indent=2)
