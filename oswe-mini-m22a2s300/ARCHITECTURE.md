# Greenfield System Design — Overview

## Goal
Replace legacy routing/appointment logic with a resilient, observable, and testable microservice architecture that ensures correctness (no silent incorrect results), supports safe migration, and meets operational SLOs.

## Capability boundaries
- API Gateway / Auth: Expose endpoints, validate auth and idempotency keys.
- Routing Service (stateless): Accept requests, validate schema, select algorithm, compute route, return deterministic path+cost.
- Graph Store (stateful): Persist canonical graph definitions, versions, and metadata.
- Orchestrator / Workflow Service: Manage long-running flow (e.g., scheduling appointments) with Saga/outbox for side effects.
- Notifier/Integration Layer: Integrate with calendar providers and downstream systems using idempotent, retriable clients.
- Observability: Centralized structured logging, metrics (latency, retries, success rate), and tracing with request_id.

## Service decomposition (microservices)
1. api-service (FastAPI): request handling, auth, idempotency middleware, input validation.
2. routing-engine (Python module): algorithm implementations (Dijkstra, Bellman-Ford, A*), selection logic, performance profiling.
3. graph-store (Postgres or Key-Value + S3): Graph metadata in SQL, large blobs in object store.
4. workflow-service (Temporal/State-machine): Long-running appointment state transitions using Saga patterns and outbox for integration.
5. integration-adapters: calendar, notification, search indexes.

## Unified state machine
- Single source-of-truth state machine for appointment lifecycle: [requested → scheduled → confirmed → notified | canceled | failed].
- Transitions are event-sourced and idempotent; each transition requires a unique request_id and persisted event in the outbox.

## Resiliency strategies
- Idempotency: `Idempotency-Key` header required for state-changing operations; persisted with TTL in DB to deduplicate.
- Retries & Backoff: Client and server side retries with exponential backoff and jitter. Use retry budgets and enforce idempotency.
- Timeouts & Circuit Breaker: Per-call timeouts; circuit-breaker protecting external dependencies (calendar provider). Circuit breaker integrates with metrics (open when p50/p95 latency threshold exceeded or error rate > x%).
- Compensation: Saga pattern for multi-step operations; if a downstream step fails beyond retries, run compensating action to undo prior steps.
- Outbox Pattern: Persist outgoing integration events atomically with state changes; a reliable background process ships them to external systems.

## Architecture & data flow (ASCII)

Client ---> API Gateway ---> API Service ---> Routing Engine ---> Graph Store
                                  |                         |
                                  v                         v
                           Workflow Service         Integration Adapters
                                  |                         |
                                  v                         v
                             Outbox Processor     External systems (calendar, email)

## Key interfaces / schemas
- POST /v2/appointments/schedule
  - Request JSON:
    {
      "request_id": "uuid",
      "idempotency_key": "string",
      "customer_id": "string",
      "start_node": "string",
      "goal_node": "string",
      "graph_version": "string?",
      "policy": { "allow_negative_weights": false }
    }
  - Constraints:
    - request_id: UUID v4
    - idempotency_key: <= 128 chars, base64-url or UUID
    - start_node/goal_node: non-empty, node names validated against graph topology
    - If policy.allow_negative_weights is false, request must be rejected if any negative weight exists

- Response JSON:
  {
    "request_id": "uuid",
    "path": ["A", "C", "D", "F", "B"],
    "cost": 1.0,
    "algorithm": "bellman-ford",
    "graph_version": "v2025-12-01",
    "warnings": ["graph_contains_negative_edges"]
  }

## Validation and field constraints
- Numeric weight: finite float, within safe bounds (e.g., -1e6..1e6). Prefer decimal for money-like constraints.
- Graph size limit for synchronous compute: e.g., ≤ 10k nodes for sync path; larger graphs require async job with notification.
- Observability: every request logs `request_id`, `idempotency_key` (hashed), `customer_id` (hashed), and non-sensitive payload.

## Migration & Parallel-run strategy
- Stage 1: Deploy routing service v2 alongside legacy; shadow traffic (read-only) to v2 for comparison; produce diffs to `results_pre.json`.
- Stage 2: Dual-write non-destructive operations; maintain read path to legacy by default, compare and log mismatches.
- Stage 3: Promote v2 for a small percentage of traffic with canary; monitor p50/p95, error rate, and reconciliation metrics.
- Cutover: Switch read/write for traffic after SLO validation over a canary window; maintain read-only legacy for rollback.
- Backfill: For state migration, run idempotent backfill jobs using a snapshot + outbox for side-effects.
- Rollback: Feature-flagged switch; drain in-flight sagas; re-sync any outbox events emitted.

## Validation and acceptance criteria
- Deterministic route decisions; zero silent incorrect results for canonical cases.
- Idempotency guarantee: repeated identical `idempotency_key` yields one state change.
- SLO: p50 latency ≤ 50ms, p95 ≤ 300ms for graphs ≤ 1k nodes (example — tune with traffic data).

