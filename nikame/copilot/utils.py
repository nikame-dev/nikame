import os
import shutil
import ast
from pathlib import Path
from typing import List, Optional

class FileManager:
    """Handles safe file mutations with backups and AST awareness."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    def create_backup(self, file_path: Path) -> Optional[Path]:
        """Create a .bak file before modification if it exists."""
        if not file_path.exists():
            return None
        bak_path = file_path.with_suffix(file_path.suffix + ".bak")
        shutil.copy2(file_path, bak_path)
        return bak_path

    def inject_import(self, file_path: Path, import_line: str) -> bool:
        """Inject an import line if not already present."""
        if not file_path.exists():
            return False
        
        content = file_path.read_text()
        if import_line in content:
            return False

        self.create_backup(file_path)
        lines = content.splitlines()
        
        # Insert at the top, but after __future__ or docstrings if possible
        insert_idx = 0
        for i, line in enumerate(lines[:10]):
            if line.startswith(("import ", "from ")):
                insert_idx = i
                break
        
        lines.insert(insert_idx, import_line)
        file_path.write_text("\n".join(lines) + "\n")
        return True

    def inject_router(self, file_path: Path, router_call: str) -> bool:
        """Inject app.include_router(...) call."""
        if not file_path.exists():
            return False
            
        content = file_path.read_text()
        if router_call in content:
            return False

        self.create_backup(file_path)
        lines = content.splitlines()
        
        # Find where 'app = FastAPI()' is or after other include_router calls
        insert_idx = len(lines)
        for i, line in enumerate(lines):
            if "app.include_router" in line:
                insert_idx = i + 1
            elif "app = FastAPI()" in line and insert_idx == len(lines):
                insert_idx = i + 1
        
        lines.insert(insert_idx, router_call)
        file_path.write_text("\n".join(lines) + "\n")
        return True

    def find_main_file(self) -> Optional[Path]:
        """Heuristic search for FastAPI entry point."""
        candidates = [
            self.root_dir / "main.py",
            self.root_dir / "app" / "main.py",
            self.root_dir / "src" / "main.py",
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    def get_function_signatures(self, file_path: Path) -> List[str]:
        """Extract function names using AST."""
        if not file_path.exists():
            return []
        try:
            tree = ast.parse(file_path.read_text())
            return [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        except:
            return []
