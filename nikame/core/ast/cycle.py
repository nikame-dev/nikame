from typing import Any

import networkx as nx


class CycleDetector:
    """Detects import cycles in a networkx directed graph."""
    
    def detect(self, graph: "nx.DiGraph[Any]") -> list[list[str]]:
        """
        Returns a list of cycles detected in the graph.
        Each cycle is represented as a list of module names.
        """
        try:
            # simple_cycles returns an iterator over all elementary circuits
            cycles = list(nx.simple_cycles(graph))
            return cycles
        except Exception:
            return []
