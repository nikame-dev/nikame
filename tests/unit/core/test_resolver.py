from pathlib import Path

from nikame.core.registry.loader import RegistryLoader
from nikame.core.registry.resolver import RegistryResolver


def test_resolve_simple_dependency(mock_registry: Path) -> None:
    # Add a pattern that depends on test.dummy
    new_pattern_dir = mock_registry / "patterns" / "test" / "dependent"
    new_pattern_dir.mkdir(parents=True)
    
    manifest = """
id: test.dependent
display_name: Dependent Pattern
version: 1.0.0
category: test
description: Depends on dummy.
requires: [test.dummy]
"""
    (new_pattern_dir / "manifest.yaml").write_text(manifest.strip())
    
    loader = RegistryLoader(mock_registry)
    resolver = RegistryResolver(loader)
    
    result = resolver.resolve("test.dependent", [])
    
    assert result.can_apply is True
    assert result.install_order == ["test.dummy", "test.dependent"]

def test_resolve_circular_dependency(mock_registry: Path) -> None:
    # A -> B, B -> A
    p1_dir = mock_registry / "patterns" / "circ" / "a"
    p1_dir.mkdir(parents=True)
    (p1_dir / "manifest.yaml").write_text("id: circ.a\nversion: 1.0.0\ndisplay_name: A\ndescription: A\nrequires: [circ.b]")

    p2_dir = mock_registry / "patterns" / "circ" / "b"
    p2_dir.mkdir(parents=True)
    (p2_dir / "manifest.yaml").write_text("id: circ.b\nversion: 1.0.0\ndisplay_name: B\ndescription: B\nrequires: [circ.a]")
    
    loader = RegistryLoader(mock_registry)
    resolver = RegistryResolver(loader)
    
    result = resolver.resolve("circ.a", [])
    
    assert result.can_apply is False
    assert "Circular dependency" in result.error_message

def test_resolve_conflicts(mock_registry: Path) -> None:
    # A conflicts with B
    p_a_dir = mock_registry / "patterns" / "conf" / "a"
    p_a_dir.mkdir(parents=True)
    (p_a_dir / "manifest.yaml").write_text("id: conf.a\nversion: 1.0.0\ndisplay_name: A\ndescription: A\nconflicts: [conf.b]")

    loader = RegistryLoader(mock_registry)
    resolver = RegistryResolver(loader)
    
    # Try to apply A when B is already there
    result = resolver.resolve("conf.a", ["conf.b"])
    
    assert result.can_apply is False
    assert any("conflicts with already applied conf.b" in c for c in result.hard_conflicts)
