# Current-state analysis (legacy `issue_project`)

Summary
- The legacy project implements a naive Dijkstra algorithm that is intentionally incorrect for graphs with negative weights. Tests assert the correct behavior but the implementation mixes two different expectations (reject negative edges OR compute shortest path using a negative-edge-capable algorithm).

Key findings
- Functionality: Dijkstra used on graphs with negative edges; early node finalization; missing negative-edge validation.
- Reliability: No simulation of external failures or side-effect safeties; pure in-process code.
- Performance: For small graphs performance adequate; no complexity guarantees or stress tests.
- Maintainability: Minimal API and no clear service boundaries; mixing of algorithm choice and validation.

Table of issues

| Category | Symptom | Likely Root Cause | Evidence / Needed Evidence |
|---|---|---|---|
| Functionality | Wrong shortest path or incorrect acceptance of negative-weight graphs | Dijkstra applied without negative-edge check; early visited set | `routing.py` marks visited on discovery; test asserts negative weight should raise or produce optimal path (contradiction) |
| Reliability | No retry, no idempotency, no outbox for side effects | Single-process script; no external systems simulated or protected | No external calls in legacy code; `KNOWN_ISSUE.md` acknowledges bug |
| Maintainability | Tight coupling of algorithm and input validation; limited extensibility | No separation of responsibilities; logic in function with flags | Files in `src/logistics` small but focused; tests assert high-level behavior without service boundaries |
| Security | No request or data sanitization documented | Not applicable in example code, but important for production | Missing logs and security policy artifacts |

High priority hypotheses and validation steps
- Hypothesis: Incorrect path due to early visited finalization. Validate: Modify algorithm to mark visited on pop; run tests and compare to expected path.
- Hypothesis: Negative-edge input should cause rejection. Validate: Add negative-edge validation that raises ValueError and run tests expecting error.
