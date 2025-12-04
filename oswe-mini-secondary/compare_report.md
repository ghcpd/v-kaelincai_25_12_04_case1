# Compare report — legacy vs prototype

Summary:

- Legacy test suite: 2 failures (see `results/results_pre.txt`) — failing behavior around running Dijkstra on negative-weight graphs.
- Prototype (v2) test suite: 5 passed (see `results/results_post.txt`) — covers idempotency, retries/backoff, circuit-breaker and outbox compensation tests.

Key metrics (from `results/aggregated_metrics.json`):

| Suite | Passed | Failed | Duration (s) |
|---|---:|---:|---:|
| legacy (pre) | 0 | 2 | 0.17 |
| prototype (post) | 5 | 0 | 0.14 |

Rollout guidance:

1. Add the outbox + state machine to the production DB schema.
2. Add adapter layer and circuit-breaker configuration around external calendar provider.
3. Deploy v2 services to staging and run shadow traffic for 24–72 hours.
4. Use the outbox replay and reconciliation worker to backfill unscheduled items, compare totals vs pre-change snapshots.
5. Convert traffic to v2 incrementally using traffic-shifting (canary) and monitor metrics (success rate, retry counts, circuit open events).

Rollback path: keep old endpoints alive during canary. If failed conditions exceed error thresholds (e.g., >1% failures at p95), shift traffic back and stop v2 until fixes applied.
