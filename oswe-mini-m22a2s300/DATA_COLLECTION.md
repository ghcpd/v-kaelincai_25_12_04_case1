# Data Collection & Missing Assumptions

## Missing data / assumptions
- Production logs and timestamps for appointment operations (create/update/cancel).
- Traffic profile: request per second, peak load, burst characteristics, error rates.
- Database schema snapshots and size (appointments table, indexes, FK constraints).
- External integrations and APIs: calendar provider, notification services, auth/identity flows.
- Transactional guarantees currently relied upon (e.g., eventual vs strong consistency).
- Existing idempotency support and correlation keys in client requests.
- Security policies: PII fields, encryption at rest/in transit, RBAC.
- Observability currently in place: metrics, logs, tracing (sample rates).

## Collection checklist
- [ ] Full codebase and dependency manifests (requirements.txt, lock files)
- [ ] Historic logs (≥7 days), including structured logs and error stacks
- [ ] Production and staging DB snapshots (schema + 1% sample of rows)
- [ ] Traffic captures / load traces (sampling or replay files)
- [ ] API contracts, OpenAPI specs, or sample request/response payloads
- [ ] CI/CD pipeline configs and rollbacks/playbook
- [ ] Monitoring dashboards and SLOs/SLA definitions
- [ ] Runbooks for incident triage and common failure modes
- [ ] Test harnesses and previous test results (integration, load tests)

## Next steps
Collect the above artifacts and provide access (or sanitized extracts) to enable accurate RCA and migration planning.
