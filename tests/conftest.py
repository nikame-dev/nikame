from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """Typer CLI runner for testing commands."""
    return CliRunner()

@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Temporary project root with a nikame.yaml."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    
    config_content = """
version: "2.0"
name: test-project
description: Test project
modules: []
environment:
  target: local
"""
    (project_dir / "nikame.yaml").write_text(config_content.strip())
    (project_dir / ".nikame").mkdir()
    
    return project_dir

@pytest.fixture
def mock_registry(tmp_path: Path) -> Path:
    """Temporary pattern registry for testing."""
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    
    # Create a dummy pattern
    pattern_dir = registry_dir / "patterns" / "test" / "dummy"
    pattern_dir.mkdir(parents=True)
    
    manifest = """
id: test.dummy
display_name: Dummy Pattern
version: 1.0.0
category: test
description: A dummy pattern for testing.
injects:
  - operation: create
    path: app/dummy.py
    template: dummy.py.j2
"""
    (pattern_dir / "manifest.yaml").write_text(manifest.strip())
    
    (pattern_dir / "templates").mkdir()
    (pattern_dir / "templates" / "dummy.py.j2").write_text("print('hello')")
    
    return registry_dir
