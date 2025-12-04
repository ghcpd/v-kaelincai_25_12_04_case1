# Missing data and key assumptions

This document lists artifacts missing from the legacy repo and key assumptions we adopt designing a greenfield replacement.

Missing items
- Production and staging logs (request/response, stack traces, latency percentiles)
- Traffic patterns and request-rate distributions
- DB snapshots or schema (if any persisted state exists beyond in-memory graphs)
- Monitoring dashboards and alert rules (SLOs/SLA definitions)
- Operational runbooks and rollback policies
- Security requirements (authN/authZ), data retention and masking rules

Assumptions for design
- System handles routing queries for directed weighted graphs; single-node in-memory service is currently used.
- No external DB was present; data is supplied as JSON files for graphs. We'll add optional durable stores (SQLite/Postgres) in design.
- Requests must be idempotent by request-id key.
- External systems can fail transiently; design should support retries/backoff, circuit-breaker, and outbox for side effects.
- Latency SLO: p95 <= 200ms for small graphs (<= 100 nodes), p95 <= 1s for medium graphs (<= 1k nodes).

If any assumption is incorrect: provide production logs, traffic snapshots, and schema access to refine the design.
