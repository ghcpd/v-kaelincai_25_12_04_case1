"""
Routing algorithms: Dijkstra and Bellman-Ford with validation and timeout support.
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional, Callable
import heapq
import time

from .graph import Graph


class TimeoutError(Exception):
    """Raised when algorithm exceeds timeout."""
    pass


def dijkstra_shortest_path(
    graph: Graph,
    start: str,
    goal: str,
    timeout_ms: int = 200,
    check_timeout: Optional[Callable] = None,
) -> Tuple[List[str], float]:
    """
    Compute shortest path using Dijkstra's algorithm.
    
    Args:
        graph: Directed weighted graph (all weights must be non-negative)
        start: Source node
        goal: Destination node
        timeout_ms: Maximum execution time in milliseconds
        check_timeout: Optional callback to check timeout externally
    
    Returns:
        (path: List[str], total_cost: float)
    
    Raises:
        ValueError: If graph contains negative weights, start/goal not in graph
        TimeoutError: If algorithm exceeds timeout_ms
    """
    # Validate preconditions
    _validate_inputs(graph, start, goal)
    _check_negative_weights(graph)
    
    # Initialize
    dist: Dict[str, float] = {start: 0.0}
    prev: Dict[str, Optional[str]] = {start: None}
    heap: List[Tuple[float, str]] = [(0.0, start)]
    visited = set()
    
    # Timeout tracking
    start_time = time.perf_counter()
    iteration_count = 0
    
    while heap:
        # Check timeout every 100 iterations
        iteration_count += 1
        if iteration_count % 100 == 0:
            if check_timeout:
                check_timeout()
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            if elapsed_ms > timeout_ms:
                raise TimeoutError(f"Dijkstra exceeded {timeout_ms}ms timeout (elapsed: {elapsed_ms:.1f}ms)")
        
        cost, node = heapq.heappop(heap)
        
        if node == goal:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return _reconstruct_path(prev, goal), cost
        
        # Skip if already visited (node finalized)
        if node in visited:
            continue
        
        # Finalize node
        visited.add(node)
        
        # Skip stale entries
        if cost > dist.get(node, float("inf")):
            continue
        
        # Relax neighbors
        for neighbor, weight in graph.neighbors(node).items():
            if neighbor not in visited:
                new_cost = cost + weight
                if new_cost < dist.get(neighbor, float("inf")):
                    dist[neighbor] = new_cost
                    prev[neighbor] = node
                    heapq.heappush(heap, (new_cost, neighbor))
    
    raise ValueError(f"No path found from {start} to {goal}")


def bellman_ford_shortest_path(
    graph: Graph,
    start: str,
    goal: str,
    timeout_ms: int = 200,
    check_timeout: Optional[Callable] = None,
) -> Tuple[List[str], float]:
    """
    Compute shortest path using Bellman-Ford algorithm.
    
    Supports negative-weight edges. Raises error if negative cycle detected.
    
    Args:
        graph: Directed weighted graph (may contain negative weights)
        start: Source node
        goal: Destination node
        timeout_ms: Maximum execution time in milliseconds
        check_timeout: Optional callback to check timeout externally
    
    Returns:
        (path: List[str], total_cost: float)
    
    Raises:
        ValueError: If start/goal not in graph or negative cycle exists
        TimeoutError: If algorithm exceeds timeout_ms
    """
    # Validate preconditions
    _validate_inputs(graph, start, goal)
    
    # Initialize
    nodes = list(graph.nodes())
    dist: Dict[str, float] = {node: float("inf") for node in nodes}
    dist[start] = 0.0
    prev: Dict[str, Optional[str]] = {node: None for node in nodes}
    
    # Timeout tracking
    start_time = time.perf_counter()
    
    # Relax edges |V|-1 times
    for iteration in range(len(nodes) - 1):
        if iteration % 10 == 0:
            if check_timeout:
                check_timeout()
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            if elapsed_ms > timeout_ms:
                raise TimeoutError(f"Bellman-Ford exceeded {timeout_ms}ms timeout (elapsed: {elapsed_ms:.1f}ms)")
        
        updated = False
        for source in graph.nodes():
            if dist[source] == float("inf"):
                continue
            for target, weight in graph.neighbors(source).items():
                new_cost = dist[source] + weight
                if new_cost < dist[target]:
                    dist[target] = new_cost
                    prev[target] = source
                    updated = True
        
        if not updated:
            break  # Early exit if no updates
    
    # Check for negative cycles
    for source in graph.nodes():
        if dist[source] == float("inf"):
            continue
        for target, weight in graph.neighbors(source).items():
            if dist[source] + weight < dist[target]:
                raise ValueError("Negative cycle detected; shortest path undefined")
    
    if dist[goal] == float("inf"):
        raise ValueError(f"No path found from {start} to {goal}")
    
    return _reconstruct_path(prev, goal), dist[goal]


def _validate_inputs(graph: Graph, start: str, goal: str) -> None:
    """Validate graph and node parameters."""
    if start not in graph.nodes():
        available = sorted(graph.nodes())
        raise ValueError(f"Start node '{start}' not found in graph. Available nodes: {available}")
    if goal not in graph.nodes():
        available = sorted(graph.nodes())
        raise ValueError(f"Goal node '{goal}' not found in graph. Available nodes: {available}")


def _check_negative_weights(graph: Graph) -> None:
    """Check for negative-weight edges; raise error if found."""
    negative_edges = graph.find_negative_edges()
    if negative_edges:
        raise ValueError(
            f"Graph contains {len(negative_edges)} negative-weight edge(s); "
            f"Dijkstra cannot proceed. Negative edges: {negative_edges}. "
            f"Use Bellman-Ford algorithm instead."
        )


def _reconstruct_path(prev: Dict[str, Optional[str]], goal: str) -> List[str]:
    """Reconstruct path from predecessor map."""
    path: List[str] = []
    node = goal
    while node is not None:
        path.append(node)
        node = prev.get(node)
    return list(reversed(path))
