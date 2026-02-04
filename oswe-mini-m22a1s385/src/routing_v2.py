from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

class Graph:
    def __init__(self):
        self._adj: Dict[str, Dict[str, float]] = {}

    def add_edge(self, source: str, target: str, weight: float):
        if source not in self._adj:
            self._adj[source] = {}
        self._adj[source][target] = weight
        if target not in self._adj:
            self._adj[target] = {}

    def neighbors(self, node: str) -> Dict[str, float]:
        return self._adj.get(node, {})

    def edges(self) -> Iterable[Tuple[str, str, float]]:
        for s, m in self._adj.items():
            for t, w in m.items():
                yield (s, t, w)

    def has_negative_weight(self) -> bool:
        return any(w < 0 for _, _, w in self.edges())


def bellman_ford(graph: Graph, start: str, goal: str) -> Tuple[List[str], float]:
    nodes = list(graph._adj.keys())
    if goal not in nodes:
        # goal not represented in graph nodes => no path
        raise ValueError(f'No path from {start} to {goal}')
    dist: Dict[str, float] = {n: float('inf') for n in nodes}
    prev: Dict[str, Optional[str]] = {n: None for n in nodes}
    dist[start] = 0.0

    for _ in range(len(nodes) - 1):
        updated = False
        for u, v, w in graph.edges():
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                prev[v] = u
                updated = True
        if not updated:
            break

    # Detect negative cycles
    for u, v, w in graph.edges():
        if dist[u] + w < dist[v]:
            raise ValueError('negative cycle detected')

    if dist.get(goal, float('inf')) == float('inf'):
        raise ValueError(f'No path from {start} to {goal}')

    path = []
    node = goal
    while node is not None:
        path.append(node)
        node = prev.get(node)
    return list(reversed(path)), dist[goal]


def dijkstra_safe(graph: Graph, start: str, goal: str) -> Tuple[List[str], float]:
    """
    Dijkstra that rejects negative weights.
    """
    if graph.has_negative_weight():
        raise ValueError('graph contains negative weight')

    import heapq
    dist = {start: 0.0}
    prev: Dict[str, Optional[str]] = {start: None}
    heap = [(0.0, start)]

    while heap:
        cost, node = heapq.heappop(heap)
        if cost > dist.get(node, float('inf')):
            continue
        if node == goal:
            path = []
            n = goal
            while n is not None:
                path.append(n)
                n = prev.get(n)
            return list(reversed(path)), cost

        for nb, w in graph.neighbors(node).items():
            new_cost = cost + w
            if new_cost < dist.get(nb, float('inf')):
                dist[nb] = new_cost
                prev[nb] = node
                heapq.heappush(heap, (new_cost, nb))

    raise ValueError(f'No path from {start} to {goal}')


__all__ = ['Graph', 'dijkstra_safe', 'bellman_ford']
