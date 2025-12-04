from __future__ import annotations
from typing import Dict, List, Tuple, Optional
import heapq

def dijkstra(graph: Dict[str, Dict[str, float]], start: str, goal: str) -> Tuple[List[str], float]:
    dist: Dict[str, float] = {start: 0.0}
    prev: Dict[str, Optional[str]] = {start: None}
    heap: List[Tuple[float, str]] = [(0.0, start)]

    visited = set()

    while heap:
        cost, node = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)

        if node == goal:
            return _reconstruct(prev, goal), cost

        for nbr, w in graph.get(node, {}).items():
            new_cost = cost + w
            if new_cost < dist.get(nbr, float("inf")):
                dist[nbr] = new_cost
                prev[nbr] = node
                heapq.heappush(heap, (new_cost, nbr))

    raise ValueError(f"No path from {start} to {goal}")


def bellman_ford(graph: Dict[str, Dict[str, float]], start: str, goal: str) -> Tuple[List[str], float]:
    nodes = list(graph.keys())
    dist = {n: float('inf') for n in nodes}
    prev: Dict[str, Optional[str]] = {n: None for n in nodes}
    dist[start] = 0.0

    for _ in range(len(nodes) - 1):
        updated = False
        for u in nodes:
            for v, w in graph.get(u, {}).items():
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    prev[v] = u
                    updated = True
        if not updated:
            break

    # Check for negative cycles
    for u in nodes:
        for v, w in graph.get(u, {}).items():
            if dist[u] + w < dist[v]:
                raise ValueError("Graph contains a negative-weight cycle")

    if dist.get(goal, float('inf')) == float('inf'):
        raise ValueError(f"No path from {start} to {goal}")

    return _reconstruct(prev, goal), dist[goal]


def _reconstruct(prev: Dict[str, Optional[str]], goal: str) -> List[str]:
    path: List[str] = []
    node = goal
    while node is not None:
        path.append(node)
        node = prev.get(node)
    return list(reversed(path))


def validate_graph_no_negative(graph: Dict[str, Dict[str, float]]):
    for u, nbrs in graph.items():
        for v, w in nbrs.items():
            if w < 0:
                raise ValueError("Graph contains negative edge weight")


def compute_shortest_path(graph: Dict[str, Dict[str, float]], start: str, goal: str, allow_negative: bool=False) -> Tuple[List[str], float, str]:
    """
    Compute shortest path. If negative weights present and allow_negative=False -> raise ValueError.
    If negative weights present and allow_negative=True -> use Bellman-Ford.
    Otherwise use Dijkstra.
    Returns tuple (path, cost, algorithm)
    """
    has_negative = any(w < 0 for u in graph for w in graph[u].values())
    if has_negative:
        if not allow_negative:
            raise ValueError("Graph contains negative edges")
        algo = 'bellman-ford'
        path, cost = bellman_ford(graph, start, goal)
    else:
        algo = 'dijkstra'
        path, cost = dijkstra(graph, start, goal)
    return path, cost, algo
