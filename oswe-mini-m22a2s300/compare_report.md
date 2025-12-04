# Compare Report — Legacy vs v2 (sample)

Summary:
- Legacy: Known silent correctness failures on negative-weight graphs.
- v2: Explicit validation + algorithm selection; tests pass for canonical cases.

Key metrics (to be produced by `run_all.sh`):
- p50/p95 latency (legacy vs v2)
- Test pass/fail counts
- Errors and retry counts
- Idempotency assertion results

Rollout guidance:
1. Shadow v2 traffic and log diffs for at least 24h across representative traffic.
2. Run reconciliation job to detect mismatches; triage top-10 mismatches by business impact.
3. Canary promote to 1% -> 10% -> 50% while monitoring SLOs and error budgets.
4. If mismatch rate > threshold (e.g., 0.1% of requests), rollback and investigate.

Rollback path:
- Feature flag off at API gateway to divert to legacy; drain v2; reconcile outbox events.
