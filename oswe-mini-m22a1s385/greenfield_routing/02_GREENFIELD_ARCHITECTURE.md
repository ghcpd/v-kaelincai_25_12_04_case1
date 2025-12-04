# Greenfield architecture

Goal
- Replace legacy script with a small, testable microservice-like module `safe_routing` that:
  - Validates inputs and algorithm preconditions
  - Selects appropriate algorithm (Dijkstra for non-negative graphs, Bellman-Ford when negatives allowed)
  - Exposes an idempotent `create_appointment` flow that uses routing and an outbox to reliably deliver notifications to downstream systems

Service decomposition
- Routing Service (library): graph model + algorithms (Dijkstra, Bellman-Ford) + validation
- Appointment Service (process): idempotency store, outbox queue, notifier client with retry/backoff & circuit breaker
- Mocks: external notifier (API v2) for integration tests

Key resilience patterns
- Idempotency: record request_id and outcome; repeated requests with same id return same result
- Retry + Backoff: exponential backoff with jitter for transient notifier failures
- Circuit Breaker: open on repeated failures; fast fail during cooldown
- Outbox: store notifications locally and deliver asynchronously with retry so primary transaction doesn't lose events
- Compensation (Saga): if downstream confirms permanent failure, compensate by undoing prior side effects (delete appointment)

APIs and Schemas (example)

POST /appointments
{
  "request_id": "uuid",
  "user_id": "string",
  "start": "A",
  "end": "B",
  "scheduled_time": "2025-12-04T10:00:00Z"
}

Fields & constraints
- request_id: required, UUID string
- user_id: required
- start/end: node ids present in graph; 1..50 chars
- scheduled_time: ISO8601 UTC; not in the past (optional validation)

Migration and parallel run
- Dual-write: During cutover, appointments created in both legacy store and new system. Use reconciliation job to ensure parity.
- Read routing decisions from new system; legacy system in read-only mode before cutover.
- Rollback: re-enable legacy write path and pause new service; replay missing events using outbox/reconciliation.
