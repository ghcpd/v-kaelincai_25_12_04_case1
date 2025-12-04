# Compare Report: Legacy vs Greenfield

## 1) Clarifications & Assumptions

- **Missing data**: production traffic patterns, SLAs/SLOs, DB schema & migrations, external dependencies, authentication/authorization model, PII handling guidelines, observability stack, deployment topology, cloud/vendor constraints, cost targets.
- **Assumptions**:
  - Domain: appointment scheduling & routing; negative weights represent incentives/discounts or penalties.
  - Legacy service is a single-process Python app using Dijkstra for routing; no external DB beyond in-memory graphs.
  - Greenfield target can introduce new services, schemas, and infra (e.g., message bus, transactional storage).
  - Idempotency keys provided by callers (or generated server-side) are acceptable.
  - We can run shadow traffic and dual-write during migration.

**Collection checklist**
- Code & configs: repo(s), dependency manifests, build artifacts, feature flags.
- Logs & traces: error spikes, timeouts, stack traces, correlation IDs.
- Traffic: volume, peak, payload examples, retry behavior, client SLAs.
- Data: DB snapshots, schema, backfill procedures, data retention/compliance constraints.
- Monitoring: dashboards, alerting thresholds, SLOs/SLA definitions.
- Ops: deployment pipelines, rollout/rollback playbooks, access controls.

## 2) Background Reconstruction (Legacy)

- **Core flow**: Compute shortest paths over a directed weighted graph. Tests reveal negative-weight edges.
- **Boundaries**: `logistics.graph.Graph` (adjacency), `logistics.routing.dijkstra_shortest_path` (routing).
- **Dependencies**: Standard library only; no persistence.
- **Uncertainties**: Real domain objects (appointments), external systems, persistence, SLAs, failure modes.

## 3) Current-State Scan & Root-Cause Analysis

| Category | Symptom | Likely Root Cause | Evidence / Needed Evidence |
|----------|---------|-------------------|----------------------------|
| Functionality | Shortest path with negative edges returns wrong path (`['A','B']` instead of optimal) | Dijkstra used despite negative edges; nodes marked visited prematurely | Failing test `test_dijkstra_finds_optimal_path_despite_negative_edge`; code comments note BUGs |
| Functionality | No rejection of negative weights | Missing validation for negative edges before running Dijkstra | Failing test `test_dijkstra_rejects_negative_weights`; `routing.py` omits checks |
| Reliability | No idempotency or retries | Stateless function; callers must handle | Need production retry behavior/logs |
| Observability | No structured logs / correlation IDs | No logging in code | Collect prod logs to confirm |
| Security | No input validation / PII masking | Not implemented | Review payload schemas |
| Maintainability | Algorithm correctness hard-coded; no strategy pattern | Single function; no abstraction for alternative algorithms (Bellman-Ford) | Code structure |
| Cost/Perf | Unknown scaling; no caching | In-memory; algorithm complexity O(E log V) but incorrect | Measure on real graphs |

**Hypothesis chain (high priority)**
- If negative weights exist, Dijkstra misbehaves → returns suboptimal paths → downstream SLA misses.
- Validation absent → negative weights slip through → incorrect routing; possible endless cycles if negative cycles exist → timeouts.
- Fix path: validate graph for negative edges; choose Bellman-Ford or Johnson's; add guardrails (timeouts, circuit breaker); add structured logging; consider shortest-path service decomposition.

## 4) Target-State Summary (Greenfield)

- **Capabilities**: Appointment lifecycle service (init→in-progress→success/failure) with routing component choosing best provider given weights (including negative incentives).
- **Services**:
  - `routing-service` (supports negative weights via Bellman-Ford/Johnson's; exposes `/route` with idempotency keys).
  - `appointment-service` (state machine, saga/outbox for downstream notifications, retries/circuit breaker, compensation).
  - `audit-service` (immutable event log + reconciliation).
- **Resilience**: timeouts, retries with jitter/backoff, circuit breakers, idempotency keys, transactional outbox.
- **Data**: Postgres for appointments & outbox; Redis for idempotency & caching; Kafka (or SQS) for events.

(Details elaborated in README.)

## 5) Migration & Parallel Run

- **Shadow traffic**: Mirror reads to new `routing-service`.
- **Dual-write**: Write appointments to legacy + new outbox; reconcile.
- **Backfill**: Snapshot legacy data → load into Postgres; maintain change-data-capture during cutover.
- **Rollback**: Feature flag to disable new writes; clear idempotency cache entries safely.

## 6) Test Coverage Plan

- Five+ integration tests covering: idempotency, retry/backoff, timeout/circuit-breaker, saga compensation/outbox, audit/reconciliation, healthy path.
- One-click runner: `run_all.sh` / `run_all.ps1` → produces `Shared/results/*.json` and logs.

## 7) Metrics & Reporting

- Capture per-test duration; compute p50/p95; count retries/idempotency hits.
- Output `results_pre.json` (legacy), `results_post.json` (greenfield), `aggregated_metrics.json`.

**Current run (2025-12-04)**
- Legacy: `exit_code=1` (2 failures) – see `Shared/results/results_pre.json`.
- Greenfield: `5 passed`; p50=0.396ms, p95=1118ms (routing timeout case), test count=5.
- Key metrics (from `results_post.json`):
  - `test_routing_timeout_breaker`: breaker_state=open, duration≈6.29s.
  - `test_booking_fail_once`: retries_booking=1, duration≈1.12s.
  - `test_idempotent_duplicate`: repeated=true, no extra bookings.

