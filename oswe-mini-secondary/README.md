# Appointment service (v2 prototype)

This folder contains a small prototype of the appointment orchestration patterns described in the design document: idempotency, transactional outbox, retry/backoff and a simple circuit-breaker.

How to run tests (from workspace root):

```bash
cd oswe-mini-secondary
./run_tests.sh
```

Files of interest:
- `src/appointment_service` - service prototype
- `mocks/calendar_mock.py` - calendar behavior simulator used by tests
- `tests/test_integration.py` - integration tests illustrating the key scenarios
