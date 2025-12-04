"""
Enhanced Graph class with validation and metadata.
"""

from __future__ import annotations
from typing import Dict, Iterable, Tuple, List, Optional
import json


class Graph:
    """Directed weighted graph with validation."""

    def __init__(self) -> None:
        self._adj: Dict[str, Dict[str, float]] = {}
        self._metadata: Dict = {}

    def add_edge(self, source: str, target: str, weight: float) -> None:
        """Add edge with validation."""
        if not isinstance(source, str) or not source:
            raise ValueError(f"Source node must be non-empty string, got {source!r}")
        if not isinstance(target, str) or not target:
            raise ValueError(f"Target node must be non-empty string, got {target!r}")
        if not isinstance(weight, (int, float)) or weight != weight:  # NaN check
            raise ValueError(f"Weight must be finite number, got {weight!r}")

        if source not in self._adj:
            self._adj[source] = {}
        self._adj[source][target] = weight
        if target not in self._adj:
            self._adj[target] = {}

    def neighbors(self, node: str) -> Dict[str, float]:
        """Get outgoing edges from node."""
        return self._adj.get(node, {})

    def nodes(self) -> Iterable[str]:
        """Get all nodes."""
        return self._adj.keys()

    def has_negative_weights(self) -> bool:
        """Check if graph contains any negative-weight edges."""
        for source in self._adj:
            for target, weight in self._adj[source].items():
                if weight < 0:
                    return True
        return False

    def find_negative_edges(self) -> List[Tuple[str, str, float]]:
        """Find all negative-weight edges."""
        negative = []
        for source in self._adj:
            for target, weight in self._adj[source].items():
                if weight < 0:
                    negative.append((source, target, weight))
        return negative

    def validate(self) -> List[str]:
        """Validate graph structure; return list of issues (empty if valid)."""
        issues = []
        if not self._adj:
            issues.append("Graph is empty (no nodes)")
        
        # Check for self-loops
        for source in self._adj:
            if source in self._adj[source]:
                issues.append(f"Self-loop detected: {source} → {source}")
        
        return issues

    def set_metadata(self, key: str, value) -> None:
        """Store metadata (version, description, etc.)."""
        self._metadata[key] = value

    def get_metadata(self, key: str, default=None):
        """Retrieve metadata."""
        return self._metadata.get(key, default)

    @staticmethod
    def from_edge_list(edges: Iterable[Tuple[str, str, float]]) -> "Graph":
        """Create graph from edge list."""
        g = Graph()
        for src, dst, w in edges:
            g.add_edge(src, dst, w)
        return g

    @classmethod
    def from_json_file(cls, path: str) -> "Graph":
        """
        Load graph from JSON file.
        
        Schema:
        {
          "version": "1.0",
          "metadata": {...},
          "edges": [
            {"source": "A", "target": "B", "weight": 5},
            ...
          ]
        }
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        g = cls()
        
        # Load metadata
        if "metadata" in data:
            for key, value in data["metadata"].items():
                g.set_metadata(key, value)
        
        # Load edges
        if "edges" not in data:
            raise ValueError("JSON file must contain 'edges' key")
        
        for e in data["edges"]:
            if not isinstance(e, dict) or "source" not in e or "target" not in e or "weight" not in e:
                raise ValueError(f"Invalid edge structure: {e}")
            g.add_edge(e["source"], e["target"], e["weight"])
        
        return g

    def to_dict(self) -> dict:
        """Serialize graph to dictionary."""
        edges = []
        for source in self._adj:
            for target, weight in self._adj[source].items():
                edges.append({"source": source, "target": target, "weight": weight})
        
        return {
            "version": "1.0",
            "metadata": self._metadata,
            "edges": edges,
        }

    def __repr__(self) -> str:
        node_count = len(self._adj)
        edge_count = sum(len(neighbors) for neighbors in self._adj.values())
        return f"Graph(nodes={node_count}, edges={edge_count})"
