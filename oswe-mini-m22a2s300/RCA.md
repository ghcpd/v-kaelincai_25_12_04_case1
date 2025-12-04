# Current-State Scan & Root-Cause Analysis

| Category | Symptom | Likely Root Cause | Evidence / Needed Evidence |
|---|---:|---|---|
| Functionality | Incorrect shortest-path when negative edges present (A→B cost 5 returned instead of cost 1). | Use of Dijkstra on graphs with negative weights; premature node finalization (visited added at discovery). | Tests (`tests/test_routing_negative_weight.py`), `KNOWN_ISSUE.md`, code comments in `routing.py` pointing to bugs. Need production failure traces and sample inputs to confirm frequency. |
| Reliability | Algorithm produces nondeterministic or wrong results under certain inputs. | No validation for input constraints; lack of alternative algorithms or fallback. | Unit test failure; absence of runtime checks in `dijkstra_shortest_path`. Need logs showing occurrences in production and frequency. |
| Performance | Potential inefficiency on large graphs; unknown scaling properties. | Naive implementation; no attention to complexity or concurrency. | Code is single-threaded; no benchmarks. Need traffic profile and graph sizes. |
| Maintainability | Code documents known bugs; tests rely on contradictory expectations; no clear module boundaries. | Legacy quick-fixes, lack of architectural ownership. | Docstrings and KNOWN_ISSUE.md. Need commit history and PRs to understand change rationale. |
| Security | Unknown — possibly insufficient masking of PII in logs or no auth in API layer (not visible). | Observability and security controls absent from this module. | No logging or masking in current module. Need system-level config and security policies. |
| Cost | Risk of rework and errors causing conversions, manual fixes, or runtime retries. | Lack of validated inputs leads to incidents and rollbacks. | No telemetry. Need incident cost records and SLO/SLA breach history.

## High-priority issue: Negative-weight handling
- Symptom: Wrong route chosen or silent acceptance of invalid input.
- Hypothesis chain A (Validation missing): Upstream data contains negative weight due to data bug → `dijkstra_shortest_path` runs without validation → incorrect result returned → downstream business makes wrong appointment decision.
  - Validation method: run CI-level mutation tests injecting negative weights; check for detection and downstream effects via integration tests and simulation of business flows.
  - Fix path: Add explicit validation to reject negative weights OR implement algorithm supporting negative edges (Bellman-Ford). Add schema constraints and defensive checks.

- Hypothesis chain B (Algorithmic bug): Dijkstra incorrectly finalizes nodes too early → even with non-negative data the algorithm can be wrong in some corner-cases. 
  - Validation method: unit tests that force relaxation after node discovery; property-based tests on random graphs ensuring optimality.
  - Fix path: Correct visited semantics (finalize on pop) and add regression tests.

## Quick remediation options (short-term vs long-term)
- Short-term: Add pre-run validation to detect negative weights and raise clear ValueError (prevents silent wrong outputs).
- Medium-term: Implement Bellman-Ford and switch algorithm when negative weights are present; add property-based tests and edge-case harness.
- Long-term: Architect a robust routing microservice with clear interfaces, idempotency, retry logic, observability, and operational SLOs.

## Evidence to collect next
- Production logs with request IDs and payloads showing negative weights (if any).
- Graph size & traffic patterns to determine algorithm/perf choices.
- Commit history for `routing.py` to understand why the bug persisted.
