# Greenfield Routing Replacement

Overview
- This folder contains a safe routing library and an appointment manager demonstrating idempotency and outbox-based delivery.

Run tests (PowerShell):
.
.\run_tests.ps1

Artifacts
- `src/safe_routing.py`: Graph + Dijkstra + Bellman-Ford + validation
- `src/appointment_manager.py`: Idempotent appointment flow, outbox, retries
- `tests/test_integration.py`: Integration tests for core crash points and recovery
