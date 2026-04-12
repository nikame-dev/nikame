from pathlib import Path

from nikame.engines.scaffold import ScaffoldEngine


def test_render_template() -> None:
    engine = ScaffoldEngine()
    template = "Hello {{ name }}!"
    context = {"name": "World"}
    
    result = engine.render_template(template, context)
    assert result == "Hello World!"

def test_write_file(tmp_path: Path) -> None:
    engine = ScaffoldEngine()
    target = tmp_path / "app" / "test.txt"
    content = "test content"
    
    success = engine.write_file(target, content)
    
    assert success is True
    assert target.exists()
    assert target.read_text() == content

def test_inject_into_file(tmp_path: Path) -> None:
    engine = ScaffoldEngine()
    target = tmp_path / "main.py"
    target.write_text("# MARKER\nprint('end')")
    
    success = engine.inject_into_file(target, "# MARKER", "print('hello')")
    
    assert success is True
    content = target.read_text()
    assert "# MARKER\nprint('hello')\nprint('end')" in content
