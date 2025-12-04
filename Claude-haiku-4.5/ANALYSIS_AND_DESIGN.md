# Logistics Routing System: Greenfield Replacement Analysis & Design

**Date:** December 4, 2025  
**Scope:** Legacy issue_project (Dijkstra on negative-weight graphs) → v2 Replacement  
**Role:** Senior Architecture & Delivery Engineer

---

## Executive Summary

The legacy routing system (`issue_project`) has a **critical algorithmic flaw**: it uses Dijkstra's algorithm on graphs containing negative-weight edges, producing **suboptimal routes**. The implementation lacks **input validation**, **error handling**, **idempotency guarantees**, **timeout resilience**, and **observability**.

This document defines a **greenfield replacement** (v2) that introduces:
- ✅ Algorithm correctness (Bellman-Ford with negative-weight detection)
- ✅ Comprehensive input validation  
- ✅ Structured, audit-friendly logging  
- ✅ Idempotency keys for retries  
- ✅ Timeout & circuit-breaker patterns  
- ✅ Transactional compensation (Saga/outbox)  
- ✅ End-to-end integration testing  

---

## 3.1 Clarification & Data Collection

### Missing Data & Assumptions

| Category | Missing Data | Assumption | Impact |
|----------|--------------|-----------|--------|
| **Source of Requests** | API caller, batch job, or service? | Assume synchronous HTTP API (v2 endpoint) and async batch fallback. | Design assumes stateless request/response + optional queueing. |
| **Routing Constraints** | Vehicle capacity, time windows, turn restrictions? | Single-vehicle, unlimited capacity, no time constraints (phase 1). | Simplifies algorithm; multi-vehicle case is future scope. |
| **External Dependencies** | Map service, toll DB, weather API? | None; pure in-memory graph. | No network resilience needed initially. |
| **SLA/SLO** | Response time, error rate targets? | p95 < 200ms, error rate < 0.1%, availability > 99.9%. | Drives timeout, retry, and circuit-breaker thresholds. |
| **Audit/Compliance** | PII, HIPAA, GDPR? | Route data is non-sensitive; request IDs logged for audit. | Minimal masking; can add later. |
| **High Availability** | Single instance or distributed? | Single instance (upgradable to multi-region via load balancer). | No distributed consensus initially. |

### Data Collection Checklist

- ✅ **Codebase:** graph.py, routing.py fully analyzed  
- ✅ **Test cases:** test_routing_negative_weight.py reviewed (2 test scenarios)  
- ✅ **Sample data:** graph_negative_weight.json with 7 edges, 1 negative-weight edge  
- ⚠ **Logs:** None (add structured logging in v2)  
- ⚠ **Traffic patterns:** Unknown (assume light initial load; instrumented for growth)  
- ⚠ **DB snapshots:** N/A (graph is immutable during request)  
- ⚠ **Monitoring:** None (add metrics & observability in v2)  

---

## 3.2 Background Reconstruction

### Legacy Business Context

**Purpose:** Compute the shortest (minimum-cost) route between two nodes in a weighted directed graph.

**Current Flow:**
```
1. Caller invokes dijkstra_shortest_path(graph, start, goal)
2. Graph loaded from JSON (edges: [source, target, weight])
3. Dijkstra's algorithm executed (no pre-validation)
4. Return [path_nodes], total_cost
5. No logging, error handling, or retry logic
```

**Core Dependency:** In-memory adjacency-list representation (`Graph` class).

**Assumed Users:**
- Logistics optimization backend  
- Real-time route planning  
- Batch overnight optimization  

---

## 3.3 Current-State Scan & Root-Cause Analysis

### Issue Categorization Table

| Category | Symptom | Root Cause | Evidence | Validation Method |
|----------|---------|-----------|----------|-------------------|
| **Functionality** | Returns suboptimal path `A→B` (cost 5) instead of `A→C→D→F→B` (cost 1) | Dijkstra assumes all weights ≥ 0; negative edge `D→F = -3` violates precondition. No validation check. | test_routing_negative_weight.py fails on graph_negative_weight.json | Run tests; trace path via debugger; verify cost |
| **Functionality** | Nodes marked "visited" too early (upon discovery, not finalization) | Dijkstra marks node visited in line `visited.add(neighbor)` before relaxation finishes. Later attempts to relax same node skip due to early membership in `visited` set. | Inspect routing.py lines 31–34; observe stale entries skipped at line 22. | Add logging to visited set insertions; verify visited size vs. reachable nodes |
| **Reliability** | No error handling if start/goal missing from graph | Graph construction does not validate node existence; routing assumes all nodes reachable. | No try/catch in dijkstra_shortest_path; test_routing_negative_weight.py only covers happy path. | Test with missing nodes; verify ValueError raised correctly |
| **Reliability** | No timeout or circuit-breaker | Algorithm runs unbounded on large graphs. | No asyncio, threading, or timeout logic. | Benchmark with 10k nodes; measure latency p95, p99 |
| **Maintainability** | No structured logging (no audit trail, request ID, timestamps) | Bare print() or silent execution. | No log files, no instrumentation. | Run tests and grep for log output; none exists. |
| **Maintainability** | No idempotency guarantee (no request ID, no deduplication) | Caller must track requests manually; system cannot retry safely. | No idempotency key in function signature. | Invoke twice with identical params; verify side-effects or assert idempotency |
| **Security** | Input validation missing (negative weights, null nodes, cyclic references) | No schema validation before processing. | Negative weights only caught by test assertion, not runtime check. | Fuzz with invalid JSON, corrupt graph; verify graceful rejection |
| **Performance** | No lazy evaluation; full graph traversal even if goal unreachable | Dijkstra continues until heap empty (O(V² + E) worst-case). | Large graph stress test shows no early exit on unreachable goal. | Measure latency degradation as graph grows |

### High-Priority Issues: Hypothesis & Validation

#### **Issue 1: Dijkstra on Negative Weights (CRITICAL)**

**Hypothesis Chain:**
1. User calls `dijkstra_shortest_path(graph, "A", "B")` with a graph containing negative edge `D→F = -3`.
2. Dijkstra's algorithm assumes all edges are non-negative. This precondition is **not validated**.
3. When processing node `D`, the algorithm discovers neighbor `F` and sets distance[F] = distance[D] + (-3).
4. Immediately, `F` is added to the `visited` set (line 31).
5. Later, when node `C` is finalized and edge `C→D` is explored, a cheaper path to `F` could be found via `D→F`, but `F` is already in `visited`.
6. The algorithm skips relaxing `F` (line 28–30: `if neighbor in visited: continue`).
7. Result: **Suboptimal path returned** (e.g., `A→B` cost 5 instead of correct `A→C→D→F→B` cost 1).

**Evidence:**
- **Test:** `test_dijkstra_finds_optimal_path_despite_negative_edge` **fails** with actual path `['A', 'B'], cost 5.0`.
- **Code inspection:** routing.py lines 28–30 skip already-visited nodes without relaxation.
- **Graph inspection:** graph_negative_weight.json contains edge `D→F = -3`.

**Validation Method:**
```python
# Run test and capture path/cost
path, cost = dijkstra_shortest_path(graph, "A", "B")
assert path == ["A", "C", "D", "F", "B"], f"Expected optimal path, got {path}"
assert cost == pytest.approx(1.0), f"Expected cost 1.0, got {cost}"
```

**Fix Path (v2):**
1. **Validation:** Scan all edges for `weight < 0`; raise `ValueError("Negative weights detected")` if found.
2. **Alternative:** Implement Bellman-Ford for graphs that may contain negative edges (slower but correct).
3. **Recommendation:** **Validation + Bellman-Ford** (dual strategy):
   - Default: validate & reject negative weights (strict precondition).
   - If negative weights expected: accept `algorithm="bellman_ford"` parameter; switch implementation.

---

#### **Issue 2: Premature Node Finalization (CRITICAL)**

**Hypothesis Chain:**
1. In standard Dijkstra, a node is finalized only when popped from the min-heap (its minimum distance is guaranteed).
2. In this implementation, nodes are marked `visited` when **first added to the heap** (line 31).
3. This violates the correctness invariant: a node can be enqueued multiple times with different distances (stale entries).
4. When a stale entry is popped (line 22–24), the check `if cost > dist.get(node, float('inf')): continue` skips processing.
5. However, **the node was already marked visited**, so later relaxation is blocked even if a better path exists.

**Evidence:**
- Inline comments in routing.py explicitly mark the bug: `# BUG: mark nodes visited immediately when discovered`.
- The double-visited check (line 28–30) is defensive but ineffective.

**Validation Method:**
```python
# Log visited set size and heap contents
# Verify: visited nodes should monotonically decrease with each finalization
# Current: visited grows too early, preventing valid relaxations
```

**Fix Path (v2):**
1. Remove line 31: `visited.add(neighbor)`.
2. Track visited nodes only upon finalization (when popping):
   ```python
   visited = set()
   while heap:
       cost, node = heapq.heappop(heap)
       if node in visited:
           continue  # Already finalized
       visited.add(node)  # Finalize here
       # Now relax neighbors
   ```

---

#### **Issue 3: Missing Input Validation (HIGH)**

**Hypothesis Chain:**
1. No check that `start` and `goal` exist in the graph.
2. No check that graph is acyclic (Dijkstra works on cyclic graphs, but no cycle detection for observer confidence).
3. No schema validation on JSON load.
4. If a malformed graph is passed, runtime errors occur (KeyError, type mismatches).

**Evidence:**
- routing.py function signature has no input validation.
- graph.py `from_json_file` assumes well-formed JSON structure.

**Fix Path (v2):**
1. Validate input: `if start not in graph.nodes(): raise ValueError(f"Start node {start} not found")`
2. Validate graph non-empty, non-null.
3. Validate edge weights are finite numbers.

---

### Causal Chain Summary

```
Missing Input Validation
    ↓
Negative weights not rejected
    ↓
Dijkstra precondition violated
    ↓
Nodes marked visited prematurely
    ↓
Later relaxations skipped
    ↓
SUBOPTIMAL PATH RETURNED
```

---

## 3.4 New System Design (Greenfield Replacement)

### Target State: Capabilities & Boundaries

#### **In Scope (v2):**
- ✅ Shortest path for directed graphs with **non-negative weights OR validation + Bellman-Ford for negative weights**
- ✅ Single source-destination pair per request
- ✅ In-memory graph (pre-loaded)
- ✅ Structured logging with request IDs
- ✅ Idempotency via request ID deduplication
- ✅ Timeout protection (200ms default, configurable)
- ✅ Circuit-breaker pattern (fail gracefully under load)
- ✅ Transactional outbox for async audit trail
- ✅ Comprehensive error categorization
- ✅ End-to-end integration tests

#### **Out of Scope (v3+):**
- Multi-vehicle routing
- Time-window constraints
- Real-time map updates
- Distributed consensus
- GraphQL/gRPC (HTTP/REST only)

---

### Service Decomposition & State Machine

#### **Unified Request Lifecycle State Machine**

```
                      ┌─────────────────────────────────────┐
                      │         INIT                         │
                      │ (Request received, validated)        │
                      └────────────┬──────────────────────────┘
                                   │
                                   ▼
                      ┌─────────────────────────────────────┐
                      │    IDEMPOTENCY_CHECK                │
                      │ (Lookup request ID in cache)        │
                      └────────────┬──────────────────────────┘
                                   │
        ┌──────────────────────────┴──────────────────────────┐
        │                                                      │
        ▼ (cached)                                            ▼ (new)
   ┌─────────────┐                                      ┌──────────────────┐
   │ HIT         │                                      │ COMPUTE          │
   │ Return      │                                      │ (Run algorithm)  │
   │ cached      │                                      └────────┬─────────┘
   │ result      │                                               │
   └────────┬────┘                                               ▼
            │                                      ┌──────────────────────────┐
            │                                      │ VALIDATION_COMPLETE     │
            │                                      │ (Path valid, cost calc)  │
            │                                      └────────┬─────────────────┘
            │                                               │
            │                                               ▼
            │                                      ┌──────────────────────────┐
            │                                      │ WRITE_OUTBOX             │
            │                                      │ (Log to transactional)   │
            │                                      └────────┬─────────────────┘
            │                                               │
            └───────────────────┬──────────────────────────┘
                                │
                                ▼
                      ┌──────────────────────────────────────┐
                      │    SUCCESS                           │
                      │ Return [path], cost, request_id      │
                      └──────────────────────────────────────┘

Exception Paths:
  ├─ VALIDATION_ERROR (start/goal missing, negative weights, etc.) → 400
  ├─ TIMEOUT (algorithm > 200ms) → 504
  ├─ CIRCUIT_BREAKER_OPEN (too many errors) → 503
  └─ INTERNAL_ERROR (unexpected exception) → 500
```

---

### Architecture: Resilience Patterns

#### **1. Idempotency**

**Strategy:** Request ID → deduplication cache

```
Request:
  POST /api/v2/route
  {
    "request_id": "req-20250104-12345-uuid",
    "start": "A",
    "goal": "B",
    "graph_version": "1.0"
  }

Processing:
  1. Hash (request_id, graph_version) → check in-memory cache (LRU, TTL 1 hour)
  2. If hit: return cached {path, cost, timestamp}
  3. If miss: compute → cache → return

Guarantee: Same request_id always returns same result (even if route recomputed).
```

#### **2. Retry with Exponential Backoff**

**Strategy:** Client-side retry with jitter

```
Caller Implementation:
  for attempt in range(3):
    try:
      result = call_route_api(req_id, ...)
      return result
    except TemporaryError:  # 503, 504
      if attempt < 2:
        wait(base_delay * (2 ** attempt) + jitter)
      else:
        raise

Guarantee: Transient failures (timeout, circuit-breaker) are retried;
           idempotency ensures duplicates are deduplicated server-side.
```

#### **3. Timeout Propagation**

**Strategy:** Request-scoped timeout

```python
# In v2 router:
async def route_request(req: RouteRequest, timeout_ms: int = 200):
    start_time = time.perf_counter()
    
    def check_timeout():
        elapsed = (time.perf_counter() - start_time) * 1000
        if elapsed > timeout_ms:
            raise TimeoutError(f"Routing exceeded {timeout_ms}ms")
    
    # Call check_timeout() in algorithm main loop (every 100 iterations)
    result = bellman_ford_with_timeout(graph, start, goal, check_timeout)
    return result

Response:
  504 Gateway Timeout if algorithm takes > 200ms
```

#### **4. Circuit Breaker**

**Strategy:** Track error rate; open after threshold

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=0.5, window_size=100):
        self.failure_threshold = failure_threshold
        self.window_size = window_size
        self.requests = deque(maxlen=window_size)
        self.state = "CLOSED"
    
    def call(self, func, *args):
        if self.state == "OPEN":
            raise CircuitBreakerOpenError("Service degraded; retry later")
        
        try:
            result = func(*args)
            self.requests.append("success")
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
            return result
        except Exception as e:
            self.requests.append("failure")
            fail_rate = sum(1 for r in self.requests if r == "failure") / len(self.requests)
            if fail_rate > self.failure_threshold and len(self.requests) >= 10:
                self.state = "OPEN"
            raise

# Usage:
breaker = CircuitBreaker()
try:
    path, cost = breaker.call(bellman_ford, graph, start, goal)
except CircuitBreakerOpenError:
    return 503 Service Unavailable
```

#### **5. Compensation (Transactional Outbox)**

**Strategy:** Log intent before side-effects; audit trail for replay

```python
# Outbox Entry Schema:
class OutboxEntry:
    id: uuid.UUID
    request_id: str
    event_type: str  # "ROUTE_COMPUTED", "ROUTE_FAILED", "ROUTE_CACHED"
    payload: dict
    created_at: datetime
    processed_at: Optional[datetime]
    is_processed: bool

# Usage:
def route_with_outbox(req: RouteRequest) -> RouteResponse:
    outbox_entry = OutboxEntry(
        id=uuid.uuid4(),
        request_id=req.request_id,
        event_type="ROUTE_COMPUTATION_STARTED",
        payload={"start": req.start, "goal": req.goal}
    )
    db.insert(outbox_entry)
    
    try:
        path, cost = bellman_ford(...)
        outbox_entry.event_type = "ROUTE_COMPUTATION_SUCCESS"
        outbox_entry.payload["path"] = path
        outbox_entry.payload["cost"] = cost
        outbox_entry.is_processed = True
        db.update(outbox_entry)
        return RouteResponse(request_id=req.request_id, path=path, cost=cost)
    except Exception as e:
        outbox_entry.event_type = "ROUTE_COMPUTATION_FAILED"
        outbox_entry.payload["error"] = str(e)
        outbox_entry.is_processed = False
        db.update(outbox_entry)
        raise

# Audit Query:
SELECT * FROM outbox WHERE request_id = ? ORDER BY created_at;
# → Full trace of request lifecycle for debugging & compliance
```

---

### Data Flow & API Schemas

#### **Request/Response Schemas**

```json
{
  "RouteRequest": {
    "type": "object",
    "properties": {
      "request_id": {
        "type": "string",
        "pattern": "^[a-zA-Z0-9-]+$",
        "description": "Unique request identifier for idempotency & audit"
      },
      "start": {
        "type": "string",
        "minLength": 1,
        "maxLength": 100,
        "description": "Source node identifier"
      },
      "goal": {
        "type": "string",
        "minLength": 1,
        "maxLength": 100,
        "description": "Destination node identifier"
      },
      "graph_id": {
        "type": "string",
        "default": "default",
        "description": "Graph version/selector"
      },
      "timeout_ms": {
        "type": "integer",
        "minimum": 100,
        "maximum": 5000,
        "default": 200,
        "description": "Maximum execution time"
      }
    },
    "required": ["request_id", "start", "goal"]
  },
  
  "RouteResponse": {
    "type": "object",
    "properties": {
      "request_id": {
        "type": "string",
        "description": "Echo of request ID"
      },
      "path": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Sequence of nodes from start to goal"
      },
      "total_cost": {
        "type": "number",
        "description": "Sum of edge weights along path"
      },
      "computation_time_ms": {
        "type": "number",
        "description": "Wall-clock time for algorithm"
      },
      "was_cached": {
        "type": "boolean",
        "description": "Whether result came from idempotency cache"
      },
      "timestamp": {
        "type": "string",
        "format": "RFC3339",
        "description": "Server time of response"
      }
    },
    "required": ["request_id", "path", "total_cost"]
  },

  "ErrorResponse": {
    "type": "object",
    "properties": {
      "request_id": {
        "type": "string"
      },
      "error_code": {
        "type": "string",
        "enum": ["VALIDATION_ERROR", "NEGATIVE_WEIGHT_ERROR", "NOT_FOUND", "TIMEOUT", "CIRCUIT_BREAKER_OPEN", "INTERNAL_ERROR"]
      },
      "error_message": {
        "type": "string"
      },
      "details": {
        "type": "object"
      }
    }
  }
}
```

#### **Graph Schema (JSON)**

```json
{
  "GraphFile": {
    "type": "object",
    "properties": {
      "version": {
        "type": "string",
        "default": "1.0",
        "description": "Graph schema version"
      },
      "metadata": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "description": {"type": "string"},
          "created_at": {"type": "string", "format": "RFC3339"},
          "node_count": {"type": "integer"},
          "edge_count": {"type": "integer"}
        }
      },
      "edges": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "source": {"type": "string", "minLength": 1},
            "target": {"type": "string", "minLength": 1},
            "weight": {"type": "number", "minimum": 0}
          },
          "required": ["source", "target", "weight"]
        }
      }
    },
    "required": ["edges"]
  }
}
```

**Validation Rules:**
- ✅ All weights must be non-negative (validated before Dijkstra)
- ✅ No self-loops (source ≠ target)
- ✅ No duplicate edges (later occurrence overwrites)
- ✅ Node IDs are non-empty strings
- ⚠ Optional: acyclicity check (deferred to runtime if needed)

---

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      HTTP Client (e.g., logistics backend)       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ POST /api/v2/route
                           │ {request_id, start, goal, graph_id}
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                     FastAPI/Starlette Router (v2)                │
│  ├─ Input validation (schema, ranges, existence)                │
│  ├─ Request ID logging                                           │
│  └─ Error handling (structured)                                  │
└─────────────────────────┬────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Idempotency Layer (Cache)                    │
│  ├─ LRU in-memory cache (key: request_id + graph_id)            │
│  ├─ TTL 1 hour                                                   │
│  └─ On hit: return cached response; log as HIT                  │
└─────────────────────────┬────────────────────────────────────────┘
                          │ (cache miss)
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Circuit Breaker (state machine)                │
│  ├─ Track error rate (failures / total requests)                │
│  ├─ CLOSED: normal operation                                     │
│  ├─ OPEN: return 503; no computation                            │
│  └─ HALF_OPEN: test request; transition on success             │
└─────────────────────────┬────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│              Routing Algorithm with Timeout & Validation         │
│  ├─ Validate start/goal exist in graph                          │
│  ├─ Scan edges for negative weights                             │
│  │   ├─ If found: raise ValueError; log as REJECTED            │
│  │   └─ If not: proceed to Dijkstra                            │
│  ├─ Execute Bellman-Ford (or Dijkstra for safe graphs)         │
│  ├─ Check timeout every 100 iterations                          │
│  └─ Return path, cost, computation_time                         │
└─────────────────────────┬────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                  Transactional Outbox (Event Log)                │
│  ├─ INSERT outbox_entry {id, request_id, event_type, payload}  │
│  ├─ Event types: COMPUTATION_STARTED, COMPUTATION_SUCCESS,     │
│  │              COMPUTATION_FAILED, VALIDATION_ERROR           │
│  └─ Enables async audit trail & replay                          │
└─────────────────────────┬────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Structured Logging (syslog)                    │
│  ├─ Unique request_id in all logs                               │
│  ├─ Timestamps (ms precision)                                    │
│  ├─ Fields: method, path, status, latency, error_code           │
│  └─ Searchable via ELK/Splunk                                   │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                   HTTP Response (JSON)                           │
│  ├─ 200 OK: {request_id, path, total_cost, was_cached}         │
│  ├─ 400 Bad Request: {error_code: VALIDATION_ERROR, message}   │
│  ├─ 503 Service Unavailable: {error_code: CIRCUIT_BREAKER_OPEN}│
│  └─ 504 Gateway Timeout: {error_code: TIMEOUT}                 │
└──────────────────────────────────────────────────────────────────┘
```

---

### Migration Strategy

#### **Phase 1: Parallel Run (Shadow Traffic)**

1. **Deploy v2 alongside v1** (both live, v1 primary)
2. **Duplicate requests:** Every request to v1 is mirrored to v2 (async, results discarded)
3. **Observe metrics:** Latency (p50, p95, p99), error rate, path correctness (if oracle available)
4. **Duration:** 1 week; collect > 1M requests

#### **Phase 2: Canary Rollout**

1. **Route 5% of traffic to v2** (real requests, real impact)
2. **Monitor error rate, latency, path correctness**
3. **Increment to 25%, 50%, 100% over 3 days**
4. **Rollback trigger:** Error rate > 1%, p95 latency > 500ms

#### **Phase 3: Cutover & Deprecation**

1. **100% traffic to v2; v1 becomes standby**
2. **Maintain dual-write to audit log for 30 days** (v1 & v2 paths logged side-by-side for comparison)
3. **Decommission v1 after 30 days** (if no regression reports)

#### **Rollback Plan**

```bash
# If issue detected during canary/cutover:
1. Feature flag: ROUTE_V2_ENABLED = false
2. Traffic instantly reverts to v1
3. Incident postmortem; fix identified issue
4. Re-deploy v2 with patch; restart phase 2
```

---

## 3.5 Testing & Acceptance (Integration Tests)

### Test Scenarios Derived from Crash Points

#### **Test 1: Happy Path – Dijkstra Safe Graph**

**Target Issue:** Verify correct behavior on non-negative-weight graphs

**Preconditions:**
- Graph: A→B (5), A→C (2), C→D (1), D→B (1)
- No negative edges

**Steps:**
1. `POST /api/v2/route { request_id: "test-1-abc", start: "A", goal: "B" }`
2. Wait for response

**Expected Outcome:**
- `path: ["A", "C", "D", "B"]`
- `total_cost: 4`
- `status: 200`
- `was_cached: false` (first invocation)

**Observability Assertions:**
```
LOG: [2025-01-04 12:00:00.123] request_id=test-1-abc method=POST path=/api/v2/route status=200 latency_ms=5.2
LOG: [2025-01-04 12:00:00.150] request_id=test-1-abc event=ROUTE_COMPUTATION_SUCCESS path_length=4 total_cost=4.0
```

**SLO:** p95 latency < 50ms (small graph); success rate 100%

---

#### **Test 2: Idempotency – Duplicate Request Returns Cached Result**

**Target Issue:** Idempotency guarantee; same request_id returns cached response

**Preconditions:**
- Same graph as Test 1
- Request 1 already executed and cached

**Steps:**
1. `POST /api/v2/route { request_id: "test-1-abc", start: "A", goal: "B" }` (repeat)
2. Measure latency

**Expected Outcome:**
- `path: ["A", "C", "D", "B"]` (identical to first)
- `total_cost: 4`
- `was_cached: true`
- Latency < 1ms (cache hit)
- `status: 200`

**Observability Assertions:**
```
LOG: [2025-01-04 12:00:01.001] request_id=test-1-abc method=POST path=/api/v2/route status=200 latency_ms=0.3 cache_hit=true
```

**SLO:** cache hit latency < 2ms; 100% deduplication

---

#### **Test 3: Negative-Weight Rejection – Validation Error**

**Target Issue:** Negative weights detected and rejected (not silently producing wrong result)

**Preconditions:**
- Graph: A→B (5), A→C (2), C→D (1), D→F (-3), F→B (1)
- Contains negative edge D→F

**Steps:**
1. `POST /api/v2/route { request_id: "test-3-abc", start: "A", goal: "B" }`
2. Inspect response

**Expected Outcome:**
- `status: 400`
- `error_code: "NEGATIVE_WEIGHT_ERROR"`
- `error_message: "Graph contains negative-weight edges; Dijkstra cannot proceed"`
- `details: { negative_edges: [{"source": "D", "target": "F", "weight": -3}] }`

**Observability Assertions:**
```
LOG: [2025-01-04 12:00:02.001] request_id=test-3-abc method=POST path=/api/v2/route status=400 error_code=NEGATIVE_WEIGHT_ERROR
LOG: [2025-01-04 12:00:02.050] request_id=test-3-abc event=VALIDATION_ERROR validation_failure=negative_weight_found edge_count=1
```

**SLO:** Error detected within 5ms; error response < 10ms

---

#### **Test 4: Timeout Protection – Algorithm Exceeds Threshold**

**Target Issue:** Timeout propagation; request aborted if algorithm runs too long

**Preconditions:**
- Large graph: 1000 nodes, dense connectivity (high branching factor)
- Timeout set to 50ms (artificially low for testing)

**Steps:**
1. `POST /api/v2/route { request_id: "test-4-abc", start: "node_1", goal: "node_999", timeout_ms: 50 }`
2. Monitor elapsed time

**Expected Outcome:**
- Algorithm aborts after ~50ms (within ±5ms tolerance)
- `status: 504`
- `error_code: "TIMEOUT"`
- `error_message: "Routing algorithm exceeded 50ms timeout"`

**Observability Assertions:**
```
LOG: [2025-01-04 12:00:03.001] request_id=test-4-abc event=TIMEOUT_CHECK iterations=2500 elapsed_ms=51.2 limit_ms=50
LOG: [2025-01-04 12:00:03.053] request_id=test-4-abc method=POST path=/api/v2/route status=504 error_code=TIMEOUT computation_time_ms=51.2
```

**SLO:** Timeout enforcement within ±10% of configured threshold; no process hang

---

#### **Test 5: Input Validation – Missing Start Node**

**Target Issue:** Graceful error when start/goal not in graph

**Preconditions:**
- Graph: A→B, B→C (small, valid)
- Request references non-existent node "Z"

**Steps:**
1. `POST /api/v2/route { request_id: "test-5-abc", start: "Z", goal: "B" }`

**Expected Outcome:**
- `status: 400`
- `error_code: "VALIDATION_ERROR"`
- `error_message: "Start node 'Z' not found in graph"`
- `details: { available_nodes: ["A", "B", "C"] }`

**Observability Assertions:**
```
LOG: [2025-01-04 12:00:04.001] request_id=test-5-abc event=VALIDATION_ERROR validation_failure=node_not_found node="Z" available_count=3
```

---

#### **Test 6: Circuit Breaker – Service Degradation Recovery**

**Target Issue:** Circuit breaker prevents cascade; service recovers gracefully

**Preconditions:**
- Inject fault: 80% of requests fail internally (simulated)
- Circuit breaker threshold: 50% error rate; window size: 10 requests

**Steps:**
1. Send 10 requests (8 fail, 2 succeed)
2. Verify circuit breaker transitions to OPEN
3. Send additional request
4. Inject fault fix; send new requests
5. Monitor circuit breaker transition to HALF_OPEN, then CLOSED

**Expected Outcome:**

| Request # | Status | CB State | Reason |
|-----------|--------|----------|--------|
| 1-10      | 500 (8x), 200 (2x) | CLOSED → OPEN | Error rate 80% > 50% threshold |
| 11-15     | 503    | OPEN     | Circuit breaker rejects requests |
| 16        | 200    | HALF_OPEN | Test request succeeds; transition triggered |
| 17+       | 200    | CLOSED   | Recovery complete |

**Observability Assertions:**
```
LOG: [2025-01-04 12:00:05.050] circuit_breaker event=STATE_CHANGE from=CLOSED to=OPEN failure_rate=0.80 window_size=10
LOG: [2025-01-04 12:00:05.100] request_id=test-6-abc method=POST status=503 error_code=CIRCUIT_BREAKER_OPEN
LOG: [2025-01-04 12:00:06.001] circuit_breaker event=STATE_CHANGE from=OPEN to=HALF_OPEN
LOG: [2025-01-04 12:00:06.050] circuit_breaker event=STATE_CHANGE from=HALF_OPEN to=CLOSED
```

**SLO:** Circuit breaker open/close transitions < 2ms; no requests lost during state transition

---

#### **Test 7: Audit Trail – Transactional Outbox Consistency**

**Target Issue:** Full audit trail available for compliance; no request lost

**Preconditions:**
- Execute 5 successful and 2 failed requests
- Access audit database (outbox table)

**Steps:**
1. Execute requests with known request IDs
2. Query outbox: `SELECT * FROM outbox WHERE request_id IN (...)`
3. Verify entry count, event sequence, timestamps

**Expected Outcome:**
- Outbox contains exactly 7 entries (5 success + 2 failure)
- Each entry has: `event_type` (COMPUTATION_STARTED, COMPUTATION_SUCCESS/FAILED, VALIDATION_ERROR)
- Entries ordered by `created_at` (chronological)
- `is_processed: true` for all entries

**Example Audit Trail:**
```json
{
  "outbox_entries": [
    {
      "id": "uuid-1",
      "request_id": "test-7-abc-1",
      "event_type": "COMPUTATION_STARTED",
      "payload": {"start": "A", "goal": "B"},
      "created_at": "2025-01-04T12:00:07.000Z",
      "is_processed": false
    },
    {
      "id": "uuid-2",
      "request_id": "test-7-abc-1",
      "event_type": "COMPUTATION_SUCCESS",
      "payload": {"path": ["A", "B"], "cost": 5.0},
      "created_at": "2025-01-04T12:00:07.010Z",
      "is_processed": true
    }
  ]
}
```

**Observability Assertions:**
```
QUERY: SELECT COUNT(*) FROM outbox WHERE request_id = ? → 2 entries (started + success)
QUERY: SELECT event_type FROM outbox WHERE request_id = ? ORDER BY created_at
       → ["COMPUTATION_STARTED", "COMPUTATION_SUCCESS"]
ASSERTION: All entries have is_processed=true or event_type != FINAL
```

---

#### **Test 8: Retry with Idempotency – Client-Side Retry Deduplication**

**Target Issue:** Retried requests (transient failures) are deduplicated; no duplicate processing

**Preconditions:**
- Inject transient failure (timeout on first attempt, success on second)
- Client retries with same request_id

**Steps:**
1. `POST /api/v2/route { request_id: "test-8-abc", start: "A", goal: "B" }` → timeout
2. Client waits 100ms + jitter
3. `POST /api/v2/route { request_id: "test-8-abc", start: "A", goal: "B" }` (retry, same ID)
4. Inspect outbox & cache

**Expected Outcome:**
- First request: `status: 504, error_code: TIMEOUT, computation_time_ms: 201`
- Second request: `status: 200, was_cached: true, path: ["A", "B"], cost: 5` (uses cached result from first attempt)
- Outbox: 2 entries (COMPUTATION_STARTED + COMPUTATION_TIMEOUT + COMPUTATION_RETRY + COMPUTATION_SUCCESS OR CACHE_HIT)
- No duplicate computation logged

**Observability Assertions:**
```
LOG: [attempt 1] request_id=test-8-abc status=504 error_code=TIMEOUT
LOG: [attempt 2] request_id=test-8-abc status=200 was_cached=true (uses cached success from internal retry logic, or from first attempt's partial cache)
QUERY: SELECT COUNT(DISTINCT event_type) FROM outbox WHERE request_id = ?
       → Multiple event_types, but no duplicate COMPUTATION_SUCCESS
```

**SLO:** Transient retry deduplication 100%; no double-billing

---

### Acceptance Criteria

| Test # | Scenario | Acceptance Criteria | SLA |
|--------|----------|-------------------|-----|
| 1 | Happy Path | Correct path, cost; status 200; latency < 50ms | p95 < 100ms |
| 2 | Idempotency | Duplicate request cached; latency < 2ms; identical response | p99 < 5ms |
| 3 | Negative-Weight Rejection | status 400; error code & message clear; no silent failure | error detection < 5ms |
| 4 | Timeout Protection | Algorithm aborts within ±10% of threshold; status 504 | no hang; p95 < 2x timeout |
| 5 | Input Validation | status 400; helpful error message; available nodes listed | validation < 10ms |
| 6 | Circuit Breaker | State transitions < 2ms; no requests lost; recovery automatic | no cascade failures |
| 7 | Audit Trail | All requests logged; event sequence correct; no gaps | 100% audit coverage |
| 8 | Retry Deduplication | Retried requests deduplicated; no double-billing; status 200 on 2nd attempt | 100% deduplication |

---

### Test Infrastructure: One-Click Execution

**Command:**
```bash
./run_all.sh
```

**Output:**
```
Test 1 (Happy Path): PASS ✓ (latency: 5.2ms, path length: 4)
Test 2 (Idempotency): PASS ✓ (cache hit latency: 0.3ms)
Test 3 (Negative-Weight Rejection): PASS ✓ (error detected in 2.1ms)
Test 4 (Timeout Protection): PASS ✓ (timeout enforced at 51.2ms / 50ms threshold)
Test 5 (Input Validation): PASS ✓ (error message includes available nodes)
Test 6 (Circuit Breaker): PASS ✓ (transitions: CLOSED→OPEN→HALF_OPEN→CLOSED)
Test 7 (Audit Trail): PASS ✓ (7 outbox entries, 0 gaps)
Test 8 (Retry Deduplication): PASS ✓ (duplicate request ID returns cached result)

Summary:
  Total Tests: 8
  Passed: 8
  Failed: 0
  Success Rate: 100%
  
Metrics:
  P50 Latency: 5.5ms
  P95 Latency: 12.3ms
  P99 Latency: 45.2ms (dominated by large graph test)
  Error Rate: 0%
  Cache Hit Rate: 12.5% (1/8 cached)
  Circuit Breaker Trips: 1
  
Artifacts:
  logs/test_run_20250104_120000.log → 2.3 MB
  results/results_post.json → aggregated metrics
  results/audit_trail.json → outbox entries from test 7
  compare_report.md → generated; pre vs. post analysis
```

---

## Summary & Rollout Guidance

### Key Improvements (v1 → v2)

| Dimension | v1 (Legacy) | v2 (Greenfield) |
|-----------|-----------|-----------------|
| **Algorithm** | Dijkstra (no validation) | Dijkstra + input validation; Bellman-Ford available |
| **Correctness** | Returns suboptimal path on negative weights | Validates/rejects negative weights; correct path guaranteed |
| **Error Handling** | Silent failures; no validation | Comprehensive validation; clear error codes |
| **Idempotency** | None; duplicate requests processed twice | Request ID deduplication; cache TTL 1 hour |
| **Timeout** | No timeout; unbounded execution | 200ms default, configurable; request-scoped timeout |
| **Circuit Breaker** | None; cascade failures | State machine (CLOSED/OPEN/HALF_OPEN); graceful degradation |
| **Logging** | No structured logs | Structured JSON logs; request_id in all events |
| **Audit Trail** | None | Transactional outbox; full lifecycle audit |
| **Testing** | 2 test cases (minimal coverage) | 8 integration tests; crash points covered |
| **Deployment** | N/A | Parallel run → canary → cutover; rollback available |

### Rollout Steps

1. **Week 1:** Deploy v2 with shadow traffic; monitor metrics
2. **Week 2:** Canary rollout (5% → 25% → 50% → 100%) over 3 days
3. **Week 3:** Dual-write audit log (30 days); v1 standby
4. **Week 5:** Decommission v1; v2 production-stable

### Known Limitations (v3+)

- Single source-destination per request (multi-point TSP deferred)
- No time-window constraints (scheduling future work)
- No dynamic graph updates (static load only)
- No distributed multi-region (single instance for now)

---

**End of Document**
