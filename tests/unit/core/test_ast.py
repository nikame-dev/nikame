from pathlib import Path

from nikame.core.ast.stubber import generate_stub


def test_generate_stub_simple_class(tmp_path: Path) -> None:
    code = """
class MyClass:
    def __init__(self, name: str):
        self.name = name
    
    def greet(self) -> str:
        return f"Hello {self.name}"
"""
    f = tmp_path / "test.py"
    f.write_text(code.strip())
    
    stub = generate_stub(f)
    
    assert "class MyClass:" in stub
    assert "def __init__(self, name: str):" in stub
    assert "def greet(self) -> str:" in stub
    assert "return" not in stub # Verification that body is stripped

def test_generate_stub_imports(tmp_path: Path) -> None:
    code = """
import os
from datetime import datetime

class Logic:
    pass
"""
    f = tmp_path / "test.py"
    f.write_text(code.strip())
    
    stub = generate_stub(f)
    
    assert "import os" in stub
    assert "from datetime import datetime" in stub
    assert "class Logic:" in stub

def test_generate_stub_nested(tmp_path: Path) -> None:
    code = """
class Outer:
    class Inner:
        def method(self):
            pass
"""
    f = tmp_path / "test.py"
    f.write_text(code.strip())
    
    stub = generate_stub(f)
    
    assert "class Outer:" in stub
    assert "class Inner:" in stub
    assert "def method(self):" in stub
