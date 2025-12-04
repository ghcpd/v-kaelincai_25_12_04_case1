from __future__ import annotations

from typing import Dict, List, Tuple
from appointments.models import Edge


class NegativeCycleError(Exception):
    pass


def bellman_ford(edges: List[Edge], source: str, target: str) -> Tuple[List[str], float]:
    # Build list of vertices
    vertices = set()
    for e in edges:
        vertices.add(e.source)
        vertices.add(e.target)
    dist: Dict[str, float] = {v: float('inf') for v in vertices}
    prev: Dict[str, str] = {}
    dist[source] = 0.0

    # Relax edges |V|-1 times
    for _ in range(len(vertices) - 1):
        updated = False
        for e in edges:
            if dist[e.source] + e.weight < dist[e.target]:
                dist[e.target] = dist[e.source] + e.weight
                prev[e.target] = e.source
                updated = True
        if not updated:
            break

    # Check for negative cycles
    for e in edges:
        if dist[e.source] + e.weight < dist[e.target]:
            raise NegativeCycleError("Negative cycle detected")

    if dist[target] == float('inf'):
        raise ValueError(f"No path from {source} to {target}")

    # Reconstruct path
    path = []
    node = target
    while node is not None:
        path.append(node)
        node = prev.get(node)
    return list(reversed(path)), dist[target]
