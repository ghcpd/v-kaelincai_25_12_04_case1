Structured logging schema

Fields:
- timestamp (ISO8601)
- level (INFO/WARN/ERROR)
- request_id (uuid or client-supplied request_id)
- user_masked (e.g., a****)
- event (string)
- state (NEW/IN_PROGRESS/COMPLETED/FAILED/CANCELLED)
- err_code (optional)
- retry_count (optional)

Masking: user_masked shows first char plus ****, do not store full PII in logs
