import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx


@dataclass
class ImportEdge:
    from_module: str
    to_module: str
    line: int
    is_relative: bool


class ImportGraphBuilder:
    def build(self, root: Path) -> "nx.DiGraph[Any]":
        graph: nx.DiGraph[Any] = nx.DiGraph()
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
                pass # Or track syntax errors
        
        return graph
