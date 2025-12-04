"""
Routing v2: Greenfield replacement for legacy Dijkstra implementation.

Provides:
  - Validated graph loading
  - Negative-weight detection & rejection
  - Dijkstra & Bellman-Ford algorithms
  - Structured logging with request IDs
  - Idempotency via request ID cache
  - Timeout protection
  - Circuit breaker pattern
  - Transactional outbox for audit trail
"""

from .graph import Graph
from .routing import dijkstra_shortest_path, bellman_ford_shortest_path
from .models import RouteRequest, RouteResponse, ErrorResponse
from .logger import StructuredLogger
from .idempotency import IdempotencyCache
from .circuit_breaker import CircuitBreaker
from .outbox import OutboxEntry, OutboxStore

__version__ = "2.0.0"
__all__ = [
    "Graph",
    "dijkstra_shortest_path",
    "bellman_ford_shortest_path",
    "RouteRequest",
    "RouteResponse",
    "ErrorResponse",
    "StructuredLogger",
    "IdempotencyCache",
    "CircuitBreaker",
    "OutboxEntry",
    "OutboxStore",
]
