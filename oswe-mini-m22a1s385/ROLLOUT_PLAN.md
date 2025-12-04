# Rollout Plan: v1.1 → v2 Migration

## Timeline Overview

```
Week 1 (Dec 3-9):   Shadow Mode    - v1.1 live, v2 silent
Week 2 (Dec 10-16): Canary         - 10% to v2
Week 3-4 (Dec 17-30): Ramp-up      - 25% → 50% → 75% → 100%
Week 5+ (Jan 2+):   Full Cutover   - v2 100% live, v1.1 fallback
```

---

## Phase 1: Shadow Mode (Week 1)

**Objective**: Validate v2 correctness without impacting users

### Deployment Steps

```
1. Deploy v2 code to staging environment
   └─ Run full integration test suite
   └─ Verify latency baseline

2. Configure shadow routing
   ├─ All requests go to v1.1 (return result to user)
   └─ Also execute v2 (log result, don't return)

3. Monitor comparison metrics
   ├─ Prediction agreement rate (target: ≥95%)
   ├─ v2 latency (target: p95 < 100ms)
   ├─ v2 error rate (target: < 0.5%)
   └─ Logging: JSON + request_id tracing
```

### Success Criteria

```
✓ v2 predictions match v1.1 on ≥95% of test cases
✓ v2 latency: p50 < 100ms, p95 < 300ms (SLA met)
✓ v2 error rate: < 0.5% (before retries)
✓ Structured logging: 100% requests tracked
✓ Audit trail: 100% predictions recorded
✓ No user-facing impact (v1.1 still live)
```

### Rollback

```
If prediction agreement < 90%:
  1. Disable v2 shadow mode (immediate)
  2. Debug: Check preprocessing, model weights, activation ranges
  3. Fix: Apply patch to v2 code
  4. Retry: Restart shadow mode with fixed code
```

---

## Phase 2: Canary (Week 2)

**Objective**: Expose 10% of users to v2 under controlled conditions

### Deployment Steps

```
1. Feature flag: Route by client_id or user_group
   ├─ 10% traffic → v2
   ├─ 90% traffic → v1.1 (main)
   └─ Clear routing rules (early users, beta program, etc.)

2. Enhanced monitoring
   ├─ Per-segment metrics (v1 vs v2)
   ├─ Latency: Measure tail latencies (p99)
   ├─ Errors: Categorize by error_code
   ├─ Alerts: Page on-call if error_rate > 1%
   └─ Dashboard: Real-time comparison

3. User communication
   ├─ Email beta testers: "You're testing v2, expect improvements"
   ├─ Support: Brief support team on expected changes
   └─ Escalation: 24/7 on-call for rapid rollback
```

### Success Criteria

```
✓ v2 error rate < 1% (over 24h)
✓ v2 latency p95 < 100ms (consistent)
✓ v2 predictions match v1.1 on ≥98% of requests (higher bar)
✓ No customer complaints (monitored via support tickets)
✓ Audit log consistency: 100% records match predictions
```

### Rollback Trigger

```
If error_rate(v2) > 1%:
  1. Immediately: Switch all traffic back to v1.1
  2. Diagnostic: Check logs for error_code patterns
  3. Fix: Apply patch / revert change
  4. Retry: Restart canary (same 10%) after 4h

If latency p95(v2) > 200ms:
  1. Immediately: Switch 10% → 5% (reduce exposure)
  2. Investigation: Profile code (preprocessing? inference?)
  3. Optimization: Reduce overhead or increase resources
  4. Retry: Ramp back up after fix confirmed
```

---

## Phase 3: Ramp-Up (Week 3-4)

**Objective**: Gradually increase v2 traffic while monitoring SLA

### Traffic Schedule

```
Day 1 (Dec 17):  10% → v2   (start of week)
Day 3 (Dec 19):  25% → v2   (Wednesday)
Day 5 (Dec 21):  50% → v2   (Friday morning)
Day 7 (Dec 23):  75% → v2   (Sunday)
Day 10 (Dec 26): 100% → v2  (after holiday buffer)
```

### Gates Between Each Step

```
Before 10% → 25%:
  ├─ Error rate(v2) < 0.5% over 48h
  ├─ Latency p95(v2) < 100ms sustained
  ├─ No customer complaints
  └─ Sign-off from: Engineering lead, On-call

Before 25% → 50%:
  ├─ Error rate(v2) < 0.5% over 48h
  ├─ Latency p95(v2) < 100ms sustained
  ├─ Audit log: 100% consistency
  ├─ No prediction accuracy degradation
  └─ Sign-off from: Product manager, On-call

Before 50% → 75%:
  ├─ All above criteria
  ├─ Error budget for week not exhausted
  └─ Sign-off from: Engineering lead, On-call

Before 75% → 100%:
  ├─ All above criteria
  ├─ Post-holiday buffer (Dec 26 = Day after Christmas)
  └─ Full sign-off from: CTO/Engineering manager
```

### Monitoring Dashboard

```
Real-Time Metrics:
  ├─ Error Rate: (errors / total) by v1 vs v2
  ├─ Latency: p50, p95, p99 for each version
  ├─ Throughput: requests/sec by version
  ├─ Retry Rate: retries / total by version
  ├─ Cache Hit Rate: idempotent requests
  └─ Confidence Distribution: histogram of confidence scores

Alerts (Page On-Call If):
  ├─ v2 error_rate > 1%
  ├─ v2 latency p95 > 300ms
  ├─ v2 circuit_breaker_state = OPEN
  ├─ v2 prediction_accuracy < 90% (if ground truth available)
  └─ v1 latency p95 > 100ms (regression detection)
```

### Rollback Procedure

```
If metrics breach SLA at any stage:

Decision: On-call engineer + product manager review
  1. Confirm anomaly (not noise)
  2. Identify root cause (logs, metrics, error_code distribution)
  3. Decide: Rollback vs. Fix-in-place

Immediate Rollback (< 5 min):
  1. Switch traffic: v2% → 0% (all to v1.1)
  2. Verify: Monitor v1.1 metrics normalize
  3. Alert: Notify engineering team + stakeholders

Investigation (4-24h):
  1. Analyze logs: grep error_code from v2 errors
  2. Check recent changes: code diff vs last stable
  3. Reproduce: Can we trigger in staging?
  4. Fix: Apply patch to v2 code

Restart Rollout (after fix):
  1. Test: Full integration suite in staging
  2. Deploy: v2 code to production
  3. Shadow mode: 48h before canary retry
  4. Gates: Same success criteria as before
```

---

## Phase 4: Full Cutover (Week 5+)

**Objective**: Complete migration to v2; retire v1.1

### Deployment Steps

```
1. Final traffic switch
   └─ Set v2 traffic to 100%
   └─ Verify v1.1 receives 0% (no gradual ramp)

2. Verify full operation
   ├─ All services routing to v2
   ├─ Health check: /api/v2/health responds 200
   ├─ Metrics: Error rate < 0.5%, latency p95 < 100ms
   └─ Logs: Structured logging capturing all requests

3. Monitoring for 7 days
   ├─ Daily SLA check
   ├─ Weekly accuracy validation
   ├─ Error trend analysis
   └─ Performance baseline lock-in

4. Retire v1.1 (after 30 days)
   ├─ Keep as emergency fallback (no traffic)
   ├─ At day 30: Decommission v1.1 code
   ├─ Archive: Git tag release + keep for audit
   └─ Docs: Update runbooks (v2 only)
```

### SLA Targets (v2)

```
Availability: 95%+ (uptime / total time)
Latency:      p50 < 100ms, p95 < 300ms
Accuracy:     ≥95% match on ground truth (if available)
Error Rate:   < 0.5% (before retries)
Recovery:     Retry recovery rate ≥95% for transient errors
```

---

## Rollback (Emergency)

### Scenario: Critical v2 Bug Found in Production

```
Detection: Error rate spike to 5%+
  1. Alerting: Automatic page on-call
  2. Validation: On-call confirms issue (not false alarm)
  3. Decision: CTO approves immediate rollback

Execution (target: < 5 minutes):
  1. Feature flag: v2 traffic → 0% (immediate)
  2. Verify: v1.1 metrics normalize within 1 minute
  3. Alert: Notify stakeholders of rollback reason
  4. War room: Post-mortem begins

Investigation (4-24 hours):
  1. Gather artifacts: Logs, metrics, error patterns
  2. Identify root cause: Code bug? Data corruption? Resource exhaustion?
  3. Fix: Apply patch + test in staging
  4. Communication: Update stakeholders on status

Restart Rollout (after fix confirmed):
  1. Full test suite: Must pass in staging
  2. Shadow mode: 48h + 95% agreement with v1
  3. Canary: 10% traffic with enhanced monitoring
  4. Ramp: Repeat phases 2-3 with same gates
```

### Root Cause Examples & Fixes

| Issue | Indicator | Fix | Time |
|-------|-----------|-----|------|
| **Preprocessing bug** | pixel_max > 1.0 | Add normalization assertion | 30 min |
| **Timeout hanging** | p95 latency > 5s | Add timeout wrapper | 30 min |
| **Memory leak** | Growing heap over time | Fix event loop cleanup | 1 hour |
| **Cascading failures** | Error rate rises exponentially | Tune circuit breaker threshold | 1 hour |

---

## Monitoring & Alerts

### Dashboard Panels

```
Panel 1: SLA Compliance
  ├─ v2 uptime (%) over last 7 days
  ├─ v2 error_rate (%) by hour
  ├─ v2 latency p95 over last 24h
  └─ Traffic split (% to v2)

Panel 2: Error Breakdown
  ├─ Error rate by error_code (FILE_NOT_FOUND, TIMEOUT, etc.)
  ├─ Retry success rate
  ├─ Circuit breaker state (CLOSED/OPEN/HALF_OPEN)
  └─ Error trend (anomaly detection)

Panel 3: Performance
  ├─ Latency distribution: p50, p95, p99
  ├─ Preprocessing time: avg, p95
  ├─ Inference time: avg, p95
  └─ Logging overhead: avg (ms)

Panel 4: Reliability
  ├─ Retry attempts per request
  ├─ Cache hit rate (idempotency)
  ├─ Timeout count by hour
  └─ Circuit breaker trips by hour
```

### Alert Rules

```
AlertName: HighErrorRate
  Condition: (error_count[5m] / total_requests[5m]) > 0.01
  Severity: Critical
  Action: Page on-call immediately

AlertName: HighLatency
  Condition: latency_p95[5m] > 300ms
  Severity: Warning
  Action: Alert on-call, investigate

AlertName: CircuitBreakerOpen
  Condition: circuit_breaker_state = "OPEN"
  Severity: Critical
  Action: Page on-call, check system health

AlertName: PredictionAccuracyDegradation
  Condition: (correct_predictions / total)[24h] < 0.90
  Severity: Critical
  Action: Page on-call, review model + predictions
```

---

## Stakeholder Communication

### Pre-Rollout (1 week before)

```
Email: Engineering + Product + Support + Customers (opt-in)
Subject: MNIST v2 Deployment - Week of Dec 3

Content:
  ✓ What: New v2 system (bug fix + reliability)
  ✓ Why: v1.1 had preprocessing regression; v2 fixes + adds resilience
  ✓ Timeline: Shadow (Dec 3) → Canary (Dec 10) → Cutover (Dec 26)
  ✓ Risk: Low (shadow → canary approach)
  ✓ User impact: None (transparent rollout)
  ✓ Support: Available 24/7 during rollout

Questions? Contact: engineering@example.com
```

### Weekly Updates (During Rollout)

```
Monday: Shadow mode summary
  ✓ Prediction agreement: 97%
  ✓ Latency p95: 98ms
  ✓ Error rate: 0.3%
  → Proceed to Canary

Friday: Canary summary (if running)
  ✓ v2 error rate: 0.4% (< 1% threshold)
  ✓ 10% users: No complaints
  ✓ Latency maintained
  → Proceed to Ramp-up next week
```

### Post-Rollout (7 days after full cutover)

```
Retrospective email:
  ✓ Timeline: Completed on schedule (Dec 26)
  ✓ Metrics: All SLA targets met
  ✓ Incidents: 0 critical issues
  ✓ Lessons: Document for team

Next steps: v1.1 decommissioning on Jan 2
```

---

## Checklist for Go/No-Go

### Before Phase 1 (Shadow)

- [ ] Code review: Architecture + v2 implementation
- [ ] Security review: Input validation, sensitive data masking
- [ ] Integration tests: 8/8 passing in staging
- [ ] Load test: Latency baseline < 100ms (p50)
- [ ] Documentation: README + deployment guide ready
- [ ] Monitoring: Dashboards + alert rules configured
- [ ] Stakeholder approval: Engineering lead + product manager

### Before Phase 2 (Canary)

- [ ] Shadow mode: 95%+ prediction agreement with v1
- [ ] Audit trail: 100% of v2 predictions logged
- [ ] Error handling: All error paths tested + working
- [ ] Rollback plan: Tested in staging
- [ ] On-call schedule: 24/7 coverage confirmed
- [ ] Customer comms: Beta users notified

### Before Phase 3 (Ramp-Up)

- [ ] Canary metrics: Error rate < 1%, latency SLA met
- [ ] Prediction accuracy: ≥98% match with v1
- [ ] Support team: Trained on v2 features
- [ ] Runbooks: Updated for v2 operations
- [ ] Feature flags: Tested + reliable

### Before Phase 4 (Full Cutover)

- [ ] Ramp-up complete: 100% of traffic ready to switch
- [ ] Final SLA check: All targets met over 7 days
- [ ] Post-incident review: Any issues found + fixed
- [ ] Stakeholder sign-off: CTO approval for full switch
- [ ] V1.1 kept: Emergency fallback ready (no traffic)

---

## Contact & Escalation

```
On-Call Engineer:      pagerduty: v2-oncall@example.com
Engineering Lead:      eng-lead@example.com
Product Manager:       product@example.com
CTO:                   cto@example.com

During Rollout:
  ├─ Issues: Page on-call immediately
  ├─ Questions: Slack #v2-rollout channel
  ├─ Updates: Daily standup @ 10am PT
  └─ Post-mortems: https://wiki.example.com/v2-incidents
```

---

**Rollout Ready ✓**

Last Updated: December 3, 2025  
Next Phase: Shadow Mode (Week of Dec 3)

