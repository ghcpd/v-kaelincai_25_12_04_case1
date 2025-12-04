# v2 Routing / Appointment Architecture Prototype

Run the test harness and inspect results:

- To run only v2 tests: `./run_tests.sh` (ensure `pytest` is installed and `PYTHONPATH` set to project root)
- To run legacy + v2 and produce a minimal compare: `./run_all.sh`

Artifacts:
- `data/` contains canonical graphs for testing
- `tests/` contains integration tests that cover idempotency, retry, timeout/circuit-breaker, compensation/outbox
- `results/results_post.json` produced after running v2 tests

Design docs:
- `ARCHITECTURE.md` — full greenfield design
- `RCA.md` — current-state analysis and root causes
- `DATA_COLLECTION.md` — checklist of missing artifacts to gather
