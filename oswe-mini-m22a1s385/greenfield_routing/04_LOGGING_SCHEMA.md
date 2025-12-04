# Structured logging schema

All logs MUST include a correlation/request id and follow JSON schema to aid reconciliation.

Example
{
  "ts": "2025-12-04T10:00:00Z",
  "level": "INFO",
  "service": "appointment-service",
  "request_id": "uuid",
  "user_id": "string",
  "event": "appointment.created",
  "message": "created appointment",
  "meta": {"node_path": ["A","B","C"]}
}

Rules
- request_id: required
- mask sensitive fields under meta.sensitive (e.g., credit_card)
- use ISO8601 UTC timestamps
