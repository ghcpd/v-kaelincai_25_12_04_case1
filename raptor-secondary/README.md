# Raptor Secondary (Greenfield Replacement)

## Overview

Greenfield appointment-routing platform with resilience, observability, and migration support. It replaces the legacy negative-weight-unsafe routing function with a modular architecture.

**Key capabilities**
- Appointment lifecycle state machine (init → in-progress → success/failure/cancelled).
- Routing service that supports negative weights (Bellman-Ford / Johnson's) with validation.
- Idempotent APIs, retries with jittered backoff, timeout propagation, and circuit breakers.
- Transactional outbox + Saga compensation for downstream actions (notifications, external scheduling).
- Structured logging (request/appointment IDs) and reconciliation/audit trail.

## Target Architecture

```
+------------------+       +------------------+        +------------------+
|  Client / API GW |<----->| Appointment Svc  |<------>| Routing Svc      |
+------------------+       +------------------+        +------------------+
          |                         |                           |
          |                         | (Outbox -> Kafka/SQS)     |
          |                         v                           |
          |                +------------------+                 |
          |                | Notification Svc |                 |
          |                +------------------+                 |
          |                         |
          |                         v
          |                +------------------+
          |                | Audit / Recon Svc|
          |                +------------------+
```

**Data stores**
- Postgres: `appointments`, `idempotency_keys`, `outbox_events`.
- Redis: idempotency cache, circuit-breaker counters, short-term routing cache.
- Kafka/SQS: outbox delivery to downstream services.

## Unified State Machine

States: `INIT` → `VALIDATING` → `ROUTING` → `BOOKING` → (`CONFIRMED` | `FAILED` | `CANCELLED`).

| From | Event | To | Notes |
|------|-------|----|-------|
| INIT | `validate_ok` | VALIDATING | schema & business rules |
| VALIDATING | `route_selected` | ROUTING | calls routing svc |
| ROUTING | `provider_reserved` | BOOKING | idempotent booking |
| BOOKING | `book_success` | CONFIRMED | emit events |
| BOOKING | `book_failed` | FAILED | compensation |
| * | `cancel` | CANCELLED | compensation for partial work |

Crash points: validation exceptions, routing timeouts, provider booking errors, outbox publish failures.

## Core Interfaces (JSON)

**POST /api/v2/appointments**
```json
{
  "idempotency_key": "uuid",
  "customer_id": "cust_123",
  "requested_time": "2025-12-04T10:00:00Z",
  "location": {"lat": 40.0, "lng": -74.0},
  "constraints": {"max_travel_minutes": 30},
  "metadata": {"notes": "mask sensitive"}
}
```
Constraints: `idempotency_key` required, max payload size 64KB, `requested_time` ISO8601, lat/lng valid ranges.

**POST /route** (Routing Svc)
```json
{
  "request_id": "uuid",
  "graph": {"edges": [{"source": "A", "target": "B", "weight": 5}]},
  "source": "A",
  "target": "B",
  "allow_negative": true
}
```
Response includes `path`, `cost`, `validated`: bool.

## Resilience Patterns

- **Idempotency**: store request hash + response in Postgres/Redis; return cached response on duplicate `idempotency_key`.
- **Retries**: Tenacity-based exponential backoff with jitter; retry on transient routing/booking errors.
- **Timeouts**: Per-call timeouts (routing 500ms, booking 2s); propagate `x-request-id` and `timeout-ms` headers.
- **Circuit breaker**: Sliding window failure rate; opens for 30s; half-open probes.
- **Outbox/Saga**: Write business state + outbox event in one transaction; separate dispatcher delivers; compensating actions registered per step.

## Migration Strategy

1. **Shadow traffic**: Mirror read-only routing requests to new service; compare results (store in `Shared/results_pre.json`).
2. **Dual-write**: Write appointments to legacy + new (feature-flagged); reconcile discrepancies daily.
3. **Backfill**: Snapshot legacy data into Postgres; CDC to keep in sync.
4. **Cutover**: Flip write path to new service; keep legacy read-only for safety.
5. **Rollback**: Disable new writes; replay outbox events from last checkpoint.

## Observability & Logging

- **Structured log schema**: `{timestamp, level, msg, request_id, appointment_id, idempotency_key, component, error?, duration_ms, retry_count, masked_fields}`.
- **Masking**: redact `metadata.notes`, PII; store hashes where needed.
- **Metrics**: success rate, p50/p95 latency, retry counts, idempotency hits, breaker state changes.
- **Tracing**: propagate `traceparent` header.

## Testing & Acceptance

**Integration tests (see `tests/`):**
1. Healthy path booking.
2. Idempotent duplicate request returns identical response, no double work.
3. Routing timeout triggers retry then breaker.
4. Booking failure triggers compensation and outbox event.
5. Audit/reconciliation detects and fixes outbox gap.

**Acceptance (examples)**
- Given a valid request with `idempotency_key`, when sent twice, then responses match and `repeat` is logged; retries=0.
- Given routing svc latency > timeout, when called, then retry with backoff occurs ≤3 times and breaker opens after threshold.
- Given booking fails once then succeeds, when saga runs, then outbox logs both try and compensation (if any), final state CONFIRMED.

## One-Click Runner

- `setup.sh` / `setup.ps1`: create venv, install deps.
- `run_tests.sh` / `run_tests.ps1`: run greenfield tests; emit `results/results_post.json` and logs.
- `Shared/run_all.sh` / `.ps1`: run legacy tests (issue_project) + greenfield; populate `Shared/results/*`.

## Folder Layout

```
raptor-secondary/
  src/appointments/  # business logic
  mocks/             # /api/v2 mock behaviors
  data/              # test fixtures
  tests/             # integration tests
  logs/              # run logs
  results/           # test outputs (post)
  Shared/            # cross-project artifacts
```

