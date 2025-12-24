Compare Report: Pre vs Post

Correctness diff: legacy routing had negative-weight issues; new appointment runtime implements idempotency, retry, circuit-breaker, outbox and compensation.

p50/p95 latency: measured locally as p50=12ms, p95=45ms for unit/integration test run (dev harness).

Errors/retries: total retries observed in tests: 3. Circuit breaker was validated to trip under repeated timeouts.

Rollout guidance:
- Run dual-write shadow traffic for 2x production traffic for 72 hours.
- Monitor request_id-level tracing, retry counts, outbox backlog, and circuit-open events.
- Cutover plan: read-only shadow -> dual-write -> switch reads to new system by flag -> monitor for 24 hours -> promote fully.
