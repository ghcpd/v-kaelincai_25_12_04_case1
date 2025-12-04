from __future__ import annotations

from typing import Dict, List, Tuple, Optional
import math


class Graph:
    def __init__(self) -> None:
        self._adj: Dict[str, Dict[str, float]] = {}

    def add_edge(self, source: str, target: str, weight: float) -> None:
        if source not in self._adj:
            self._adj[source] = {}
        self._adj[source][target] = weight
        if target not in self._adj:
            self._adj[target] = {}

    def neighbors(self, node: str) -> Dict[str, float]:
        return self._adj.get(node, {})

    def nodes(self):
        return list(self._adj.keys())

    @staticmethod
    def from_edge_list(edges):
        g = Graph()
        for s, t, w in edges:
            g.add_edge(s, t, w)
        return g


def has_negative_edge(graph: Graph) -> bool:
    for src in graph.nodes():
        for w in graph.neighbors(src).values():
            if w < 0:
                return True
    return False


def dijkstra(graph: Graph, start: str, goal: str) -> Tuple[List[str], float]:
    # Standard Dijkstra that finalizes nodes when popped from heap
    import heapq

    dist = {start: 0.0}
    prev = {start: None}
    heap = [(0.0, start)]

    visited = set()

    while heap:
        cost, node = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)
        if node == goal:
            return _reconstruct(prev, goal), cost

        for n, w in graph.neighbors(node).items():
            new_cost = cost + w
            if new_cost < dist.get(n, math.inf):
                dist[n] = new_cost
                prev[n] = node
                heapq.heappush(heap, (new_cost, n))

    raise ValueError(f"No path from {start} to {goal}")


def bellman_ford(graph: Graph, start: str, goal: str) -> Tuple[List[str], float]:
    nodes = graph.nodes()
    dist = {n: math.inf for n in nodes}
    prev = {n: None for n in nodes}
    dist[start] = 0.0

    for _ in range(len(nodes) - 1):
        updated = False
        for u in nodes:
            for v, w in graph.neighbors(u).items():
                if dist[u] + w < dist.get(v, math.inf):
                    dist[v] = dist[u] + w
                    prev[v] = u
                    updated = True
        if not updated:
            break

    # Check negative cycles
    for u in nodes:
        for v, w in graph.neighbors(u).items():
            if dist[u] + w < dist.get(v, math.inf):
                raise ValueError("Graph contains negative-weight cycle")

    if dist.get(goal, math.inf) == math.inf:
        raise ValueError(f"No path from {start} to {goal}")

    return _reconstruct(prev, goal), dist[goal]


def _reconstruct(prev: Dict[str, Optional[str]], goal: str) -> List[str]:
    path = []
    node = goal
    while node is not None:
        path.append(node)
        node = prev.get(node)
    return list(reversed(path))


def shortest_path(graph: Graph, start: str, goal: str, allow_negative: bool = False):
    """
    Compute shortest path with validation.
    If negative edges are present and allow_negative is False -> raise ValueError
    If negative edges present and allow_negative True -> use Bellman-Ford
    """
    if has_negative_edge(graph):
        if not allow_negative:
            raise ValueError("negative weights detected")
        return bellman_ford(graph, start, goal)
    else:
        return dijkstra(graph, start, goal)
