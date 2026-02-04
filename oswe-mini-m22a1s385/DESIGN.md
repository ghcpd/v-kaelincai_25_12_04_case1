# Greenfield Replacement Design — Routing & Appointment Lifecycle

This document outlines a greenfield design for a service that manages appointment lifecycle while performing cost-optimized routing decisions across a weighted directed graph. The design focuses on safety (no negative-weight surprises), idempotency, retries, timeouts, circuit-breakers, and saga-style compensation for side-effects.

Key principles
- Reject invalid input fast (negative weights) or use an algorithm that supports them (Bellman-Ford).
- Idempotency keys for scheduling API to avoid duplicate side-effects during retries or timeouts.
- Retry with exponential backoff and jitter for transient downstream failures; circuit breaker to prevent cascading failures.
- Transactional outbox or Saga pattern for bridging eventual-consistency side-effects (notifications, writes to external systems).

High-level architecture

Client -> API Gateway -> Appointment Service (orchestrator) -> Routing Service -> Data store / Outbox -> Downstream Systems

ASCII diagram

    [Client]
	  |
    [API GW]
	  |
  +----v-------------------------+
  | Appointment Service (orchestrator) |
  +----+------------------------+
	  |                        |
  [Routing Service]        [Outbox / Event log]
	  |                        |
  [Graph DB / Store]     [Delivery workers -> external systems]

Core interfaces
- POST /appointments {idempotency_key?, payload} -> 202 SCHEDULED with appointment id
- POST /appointments/:id/confirm -> triggers send_action with retries
- GET /appointments/:id -> status

Data model: Appointment JSON

{
  "id": "<uuid>",
  "idempotency_key": "<string>",
  "payload": { ... },
  "status": "init|scheduled|confirmed|failed|cancelled",
  "attempts": 0
}

Validation rules
- Graph edges: weight must be numeric. Reject if negative and user requested Dijkstra, or transparently run Bellman-Ford.

Migration strategy (parallel-run / cutover)
- Phase 1: Shadow reads — v2 computes paths, logs differences, but does not change final responses.
- Phase 2: Dual-write — both v1 and v2 write to DB/outbox; use reconciliation tool to compare results and surface mismatches.
- Phase 3: Read switch — route reads to v2 for non-critical traffic, monitor; increase traffic progressively.
- Phase 4: Cutover — switch writes to v2 only; keep v1 as fallback for a rollback window.

Rollback: Re-enable v1 read/write path and replay missed events from outbox if necessary.

Observability and metrics
- per-request appointment_id and idempotency_key
- metrics: success_rate, retry_count, p50/p95 latency, circuit_breaker_trips
- logs: structured JSON; mask sensitive fields

