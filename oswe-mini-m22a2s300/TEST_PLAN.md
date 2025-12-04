# Integration Test Plan — Key Scenarios

This plan maps crash points and risks to repeatable integration tests implemented under `tests/`.

Test cases (>=5):

1) Healthy path — deterministic shortest path
- Target issue: correctness on standard inputs
- Preconditions/Data: graph without negative edges (see `data/healthy_graph.json`)
- Steps: call compute_shortest_path(start, goal)
- Expected outcome: deterministic path and cost via Dijkstra
- Observability assertions: log includes `request_id`, `algorithm=dijkstra`, p50/p95 latency recorded

2) Negative weight rejection (guardrail)
- Target issue: silent acceptance of negative edges
- Preconditions/Data: graph with negative edge (see `data/graph_negative_weight.json`)
- Steps: call compute_shortest_path(..., allow_negative=False)
- Expected outcome: raise ValueError with message containing "negative"
- Observability: error metric incremented; structured log with masked `idempotency_key`

3) Negative weight handling via Bellman-Ford
- Target issue: correctness when negative edges allowed
- Preconditions/Data: same as (2), allow_negative=True
- Steps: call compute_shortest_path with allow_negative True
- Expected outcome: correct path (cost=1), algorithm=bellman-ford
- Observability: log includes algorithm selection and warnings

4) Idempotency guarantee
- Target issue: duplicate requests causing multiple state changes
- Preconditions/Data: idempotency store empty
- Steps: send two identical requests with same `idempotency_key`
- Expected outcome: single side-effect executed, second call returns cached result
- Observability: idempotency metrics and logs showing deduplication

5) Retry/backoff and timeout/circuit breaking
- Target issue: transient external failures cause cascading failures or inconsistent state
- Preconditions/Data: simulated flaky external integration
- Steps: run operation that retries, then simulate timeout to trigger circuit-breaker
- Expected outcome: successful retry with backoff, circuit breaker opens after failure threshold
- Observability: metrics for retries, circuit-breaker state change events, and latency histograms

6) Compensation / Saga & Outbox
- Target issue: partially completed multi-step workflows left in inconsistent state
- Preconditions/Data: multi-step flow with one step failing
- Steps: run flow; cause downstream failure; observe compensation step executed
- Expected outcome: state reconciled, compensation recorded in outbox and emitted
- Observability: outbox contains compensate event; audit trail with request_id and timestamps

Acceptance criteria (example)
- Given: canonical test graphs and simulated external integrations
- When: running the full test suite 100 times
- Then: 100% deterministic correctness on canonical cases; idempotency property holds; retry/backoff reduces failure rate to acceptable bounds.

SLO targets (example)
- p50 latency ≤ 50ms, p95 ≤ 300ms for graphs ≤ 1k nodes
- Error rate ≤ 0.1% on canary traffic

One-click fixture
- `./run_tests.sh` (or `python -m pytest`) runs all test scenarios and writes `results/results_post.json` with basic metrics.
