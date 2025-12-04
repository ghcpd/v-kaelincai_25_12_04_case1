1. Scope & Assumptions

1.1 Missing data / assumptions
- Production traffic patterns, peak RPS, and latency SLOs are not provided (assume <100rps per region).
- Persistent storage type is unknown; we assume relational DB with ACID support for canonical state.
- No current tracing or global request_id propagation; implement unique request_id per external request.
- External calendar API is unreliable with transient failures and occasional timeouts.

1.2 Collection checklist (what to capture)
- Code: full repository, dependencies, integration points
- Logs: 30 days of production logs, structured logs or raw
- Traffic: sampling of 1% of requests and peak-hour traces
- DB snapshots: schema dumps and sample rows for appointments and outbox
- Monitoring: dashboards for request latency, retries, outbox backlog, error rates
- Runbooks: current recovery steps and rollback paths

2. Background Reconstruction (inferred)
- Legacy project implements routing (Dijkstra) for logistics; known bug: negative-weight edges and premature finalization.
- Likely business: routing/appointment scheduling where correctness of shortest path impacts scheduling decisions.
- Dependencies: local JSON data files, internal graph module; no external service integration visible in codebase.
- Uncertainties: real transactional boundaries, multi-region replication, and external calendar service behavior.

3. Current-State Scan & Root-Cause Analysis
Table: Category | Symptom | Likely Root Cause | Evidence / Needed Evidence
- Functionality | Incorrect route on graphs with negative edges | Algorithm marks nodes visited upon discovery and omits negative-weight validation | routing.py comments and failing tests
- Reliability | No idempotency for appointment creation; risk of duplicates | No idempotency keys or transactional outbox | code review; no request_id usage
- Performance | Unknown backpressure handling on external APIs | No retry/backoff or circuit-breaker | legacy code lacks retry logic; tests show need
- Maintainability | Monolithic logic with poor separation of concerns | Missing clear API boundaries and mocks | code structure and lack of tests
- Security | No structured logging with sensitive masking | No logging in legacy code | absence of logging; design requires masking PII

High-priority Issue: Missing idempotency + external side effects
Hypothesis chain: Lack of idempotency -> Duplicate external calendar events -> Inconsistent state -> Manual reconciliation
Validation: Run tests that try duplicate creates and assert single outbox event and idempotent processing (covered by tests/test_appointment_idempotency.py)
Fix path: Implement idempotent create + transactional outbox + reconciliation job (done in new design)

4. New System Design (Greenfield Replacement)

4.1 Target State (boundaries & properties)
- Service boundary: Appointment API that owns appointment lifecycle and external calendar interactions.
- Properties: Idempotent create, transactional outbox, retry with exponential backoff, circuit breaker, timeouts, reconciliation job, compensation path.
- State machine: NEW -> IN_PROGRESS -> COMPLETED / FAILED / CANCELLED (see ASCII diagram below).

4.2 Service Decomposition
- api/ (ingest requests, validate, idempotency)
- service/ (business logic, state machine, outbox)
- worker/ (outbox processor, retry/reconciliation)
- mocks/ (external calendar API for tests)

4.3 State Machine (ASCII):

NEW -> (outbox enqueued) -> IN_PROGRESS -> (external success) -> COMPLETED
                      \-> (external failure + retries exhausted) -> FAILED
                      \-> (external success but DB commit fails) -> COMPENSATE -> CANCELLED

4.4 Idempotency and Sagas
- Idempotency key: client-supplied request_id or server generated; used to dedupe creates.
- Outbox pattern: record event in DB alongside state change, commit together, process outbox asynchronously.
- Compensation: For external side-effects that succeed but DB fails, run undo action (calendar cancel) from outbox compensation.

4.5 Interfaces / Schemas (JSON)
- POST /appointments
  Request body:
    {
      "request_id": "string",  // required idempotency key, max 128 chars
      "when": "ISO8601 datetime", // required
      "user": "string" // required, PII masked in logs
    }
  Response (201):
    {"request_id": "string", "state": "NEW", "created_at": "iso"}

Field constraints:
- request_id: regex [A-Za-z0-9\-_.]{1,128}
- when: ISO8601 with timezone; stored as UTC
- user: non-empty string; masked in logs (only first char + masked)

4.6 Validation
- Reject malformed request_id or datetime with 400
- Enforce max payload size and timestamps not in the past > 1 year

4.7 Migration & Parallel Run
- Start with read-only shadowing of incoming traffic to v2 for 72 hours.
- Backfill: run reconciliation process that replays existing appointments to populate outbox and validate idempotency.
- Cutover strategy:
  1. Shadow traffic (v2 reads, no writes)
  2. Dual-write (both v1 and v2 write) with consistent hashing of request_id for comparability
  3. Read switch to v2 by feature flag
  4. Monitor metrics for 24-72 hours
  5. Final cutover
- Rollback: re-enable reads/writes to v1, run compensation to neutralize v2 side effects.

5. Testing & Acceptance (derived integration tests)

5.1 Repeatable integration tests (derived from risks):
- Test A: Idempotency
  Preconditions: empty DB
  Steps: Create appointment twice with same request_id
  Expected outcome: single record created, one outbox event
  Observability: logs show one request_id; outbox length==1

- Test B: Retry with backoff
  Preconditions: mock calendar fails twice then succeeds
  Steps: process outbox
  Expected outcome: succeeded after retries (<=max_retries)
  Observability: metrics: retry_count==2, event delivered

- Test C: Timeout propagation & circuit breaker
  Preconditions: mock calendar times out
  Steps: process outbox until circuit opens
  Expected outcome: circuit transitions to OPEN and subsequent calls fail fast
  Observability: circuit_open metric increments, outbox backlog grows

- Test D: Compensation / Saga
  Preconditions: external call returns success, DB commit fails
  Steps: simulate post-success DB failure
  Expected outcome: compensation executed (external cancel called), appointment state CANCELLED
  Observability: audit log with compensation action and request_id

- Test E: Reconciliation
  Preconditions: outbox contains undelivered events
  Steps: run reconcile job
  Expected outcome: outbox cleared, events delivered, idempotency preserved
  Observability: outbox length==0, reconciliation logs

Acceptance criteria (Given-When-Then):
- Given network flakiness up to N transient errors, when outbox is processed, then events are delivered within M retries with success_rate>=99.9% under test harness.
- SLA: end-to-end appointment creation p95 latency <= 500ms for healthy path; system degrades gracefully under external failures.

6. Operational & Logging
- Structured logging fields: timestamp, level, request_id, user_masked, event, state, err_code, retry_count
- Masked fields: user -> show first char + ****
- Tracing: attach request_id to all logs and metrics

7. One-click test fixture
- run_all.sh executes the test suite and produces results/*.json and logs/*.txt (already included)

8. Next steps & open questions
- Confirm production SLOs, RPS, durable storage choice
- Confirm external API contract for compensation operations (cancel semantics)
- Decide on deployment model: serverless vs containers vs k8s

Appendix: Sample API Create JSON
{"request_id": "req-123", "when": "2025-12-04T10:00:00Z", "user": "alice"}

