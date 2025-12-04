# Compare Report

This repo includes a greenfield design to replace legacy routing code. The `results/` folder will contain pre/post run metrics and differences.

Rollout guidance: Start with read-only shadowing (dual-write) and monitor idempotency metrics and retry counts; ensure compensation path is tested before write cutover.
