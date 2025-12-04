# Acceptance Criteria & SLOs

Functional acceptance
- Canonical route correctness: For provided canonical graphs, v2 returns expected path and cost.
- Negative-weight handling: By default, reject negative graphs with clear error; when allowed, compute correct path via Bellman-Ford.
- Idempotency: Repeated requests with same `idempotency_key` produce a single side-effect and return the same result.

Observability & Reliability
- Structured logging containing `request_id`, hashed `idempotency_key`, and algorithm selection.
- Metrics: p50 latency ≤ 50ms, p95 ≤ 300ms (tunable after traffic analysis).
- Retrying succeeds for transient errors; circuit-breaker opens on sustained failures.

Operational
- Run `./run_tests.sh` to exercise all test scenarios; `results/results_post.json` must be generated.
- Canary stability: zero critical mismatches in canary window; mismatch threshold <= 0.1%.

Rollout exit criteria
- All acceptance tests pass on canary traffic for at least 24h.
- Observability indicates no regressions in key metrics (latency, error rate, retries).
