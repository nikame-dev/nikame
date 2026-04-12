import pytest
from pathlib import Path
from nikame.engines.rollback import RollbackEngine
from nikame.engines.verify import SyntaxVerifier
from nikame.infra.docker import DockerfileGenerator, ComposeGenerator
from nikame.core.config.schema import NikameConfig
from nikame.core.manifest.schema import ManifestV2
from datetime import datetime

# --- Rollback Tests ---

def test_rollback_system(tmp_path):
    root = tmp_path
    f1 = root / "f1.txt"
    f1.write_text("v1")
    
    engine = RollbackEngine(root)
    snap_id = engine.create_snapshot([f1], label="v1_snap")
    
    f1.write_text("v2")
    assert f1.read_text() == "v2"
    
    engine.restore_snapshot(snap_id)
    assert f1.read_text() == "v1"

# --- Verify Tests ---

def test_syntax_verifier_python(tmp_path):
    root = tmp_path
    (root / "good.py").write_text("x = 1")
    (root / "bad.py").write_text("x = [") # Broken
    
    verifier = SyntaxVerifier(root)
    result = verifier.verify()
    
    assert not result.passed
    assert "bad.py" in result.type_errors

# --- Infra Tests ---

def test_docker_generators():
    config = NikameConfig(name="testapp", modules=["database.postgres"])
    manifest = ManifestV2(
        nikame_version="2.0.0",
        project_name="testapp",
        created_at=datetime.now(),
        patterns_applied=[]
    )
    
    # Check Dockerfile
    df_gen = DockerfileGenerator()
    df_content = df_gen.generate(config)
    assert "FROM ghcr.io/astral-sh/uv" in df_content
    assert "EXPOSE 8000" in df_content
    
    # Check Compose
    c_gen = ComposeGenerator()
    c_content = c_gen.generate(config, manifest)
    assert "api:" in c_content
    assert "version: '3.8'" in c_content
