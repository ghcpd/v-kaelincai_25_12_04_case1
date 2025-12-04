# Background Reconstruction — Legacy System (inferred)

## Quick inference
- The visible code implements routing and graph utilities used by an application that computes optimal paths — likely for appointment logistics, routing, or schedule optimization.
- Canonical flow: client requests a route (start→goal) → service validates graph → computes shortest path → returns path + cost.

## Core business flows (inferred)
1. Load graph topology (edges) from JSON or DB snapshot.
2. Validate graph (nodes, weights, weight sign constraints).
3. Compute shortest path and return route and cost.
4. Upstream components use route to make scheduling or assignment decisions (appointments, deliveries).

## Boundaries and dependencies
- Internal: `Graph` and `routing` modules provide core computations.
- External: data storage for graph definitions, client-facing API, possibly calendar/booking services, notification/email services.
- Observability: tests and a KNOWN_ISSUE file indicate limited runtime protections (no negative-weight checks, limited logging).

## Highlighted uncertainties
- Is the graph always expected to have non-negative weights? Documentation unclear.
- Size of graphs (small topologies vs large routing graphs) — impacts algorithm selection (Dijkstra vs Bellman-Ford vs Johnson).
- Performance constraints: latency SLOs for route queries are unknown.
- Failure modes in production: how often negative weights occur or are caused by upstream data errors.
- Security & privacy requirements around route metadata or user-identifying data.

## Immediate implications for a greenfield design
- Must enforce input validation and explicit schema (weights type and bounds).
- Provide algorithm selection based on graph characteristics and expected SLOs.
- Add idempotency, observability, structured logging, and robust testing around negative or malformed graphs.
