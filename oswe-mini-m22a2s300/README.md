OSWE Mini: Appointment replacement greenfield

This repository contains a minimal greenfield replacement for an appointment scheduling system. It includes service runtime code, mocks, tests and scripts to run the full suite of integration tests.

Run tests: ./run_tests.sh

Acceptance criteria (dev):
- All integration tests pass locally (idempotency, retry/backoff, circuit-breaker, compensation, reconciliation).
- Unique request_id present in every log line; sensitive fields masked.

One-click: ./run_all.sh will run the test suite and generate results/*.json and logs/*.txt
