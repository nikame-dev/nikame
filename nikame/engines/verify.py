import time
from dataclasses import dataclass
from pathlib import Path

from nikame.core.ast.cycle import CycleDetector
from nikame.core.ast.graph import ImportGraphBuilder


@dataclass
class VerificationResult:
    passed: bool
    cycles: list[list[str]]
    missing_imports: list[str]
    type_errors: list[str]
    duration_ms: float


class SyntaxVerifier:
    """Service for performing static code analysis and verification."""
    
    def __init__(self, root: Path) -> None:
        self.root = root
        self._builder = ImportGraphBuilder()
        self._detector = CycleDetector()

    def verify(self) -> VerificationResult:
        """Runs the verification suite against the project root."""
        start_time = time.time()
        
        # 1. Syntax checks
        syntax_errors = []
        for py_file in self.root.rglob("*.py"):
            if not self.verify_file(py_file):
                syntax_errors.append(str(py_file.relative_to(self.root)))
                
        # 2. Build import graph
        graph = self._builder.build(self.root)
        
        # 3. Detect cycles
        cycles = self._detector.detect(graph)
        
        duration_ms = (time.time() - start_time) * 1000
        
        passed = len(cycles) == 0 and len(syntax_errors) == 0
        
        return VerificationResult(
            passed=passed,
            cycles=cycles,
            missing_imports=[],
            type_errors=syntax_errors, # Use type_errors field for syntax issues for now
            duration_ms=duration_ms,
        )

    def verify_file(self, path: Path) -> bool:
        """Simple syntax check for a single file."""
        try:
            import ast
            ast.parse(path.read_text())
            return True
        except Exception:
            return False
