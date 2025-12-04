Structured logging schema

- request_id: string, uuid v4, required
- appointment_id: string, uuid v4, optional
- timestamp: float (epoch seconds), required
- level: one of [DEBUG, INFO, WARN, ERROR], required
- event: short string, required
- payload: object, optional; mask sensitive fields (ssn, email, phone)

Masking rules: replace characters except last 2 with '*', keep domain for emails.
