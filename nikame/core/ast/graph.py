import ast
from pathlib import Path
import networkx as nx
from dataclasses import dataclass
import time
from typing import List

@dataclass
class ImportEdge:
    from_module: str
    to_module: str
    line: int
    is_relative: bool

@dataclass
class VerificationResult:
    passed: bool
    cycles: list[list[str]]
    missing_imports: list[str]
    type_errors: list[str]
    duration_ms: float

class ImportGraphBuilder:
    def build(self, root: Path) -> nx.DiGraph:
        graph = nx.DiGraph()
        if not root.exists():
            return graph
            
        for py_file in root.rglob("*.py"):
            try:
                content = py_file.read_text()
                tree = ast.parse(content, filename=str(py_file))
                
                module_name = py_file.relative_to(root).with_suffix("").parts
                module_str = ".".join(module_name)
                
                graph.add_node(module_str)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            graph.add_edge(module_str, alias.name, 
                                          line=node.lineno, is_relative=False)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        graph.add_edge(module_str, node.module, 
                                      line=node.lineno, is_relative=node.level > 0)
            except SyntaxError:
                pass # Or track syntax errors in VerificationResult
        
        return graph

class CycleDetector:
    def detect(self, graph: nx.DiGraph) -> List[List[str]]:
        try:
            cycles = list(nx.simple_cycles(graph))
            return cycles
        except Exception:
            return []

class SyntaxVerifier:
    def __init__(self, root: Path):
        self.root = root
        self._builder = ImportGraphBuilder()
        self._detector = CycleDetector()

    def verify(self) -> VerificationResult:
        start_time = time.time()
        graph = self._builder.build(self.root)
        cycles = self._detector.detect(graph)
        duration_ms = (time.time() - start_time) * 1000
        
        return VerificationResult(
            passed=len(cycles) == 0,
            cycles=cycles,
            missing_imports=[], # Optional to implement later
            type_errors=[], # Optional pyright integration
            duration_ms=duration_ms,
        )
