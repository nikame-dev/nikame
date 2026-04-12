import pytest
from nikame.cli.main import cli
from pathlib import Path

def test_cli_list(cli_runner, mock_registry):
    """Verifies that the 'nikame list' command works."""
    result = cli_runner.invoke(cli, ["list", "--registry", str(mock_registry)])
    assert result.exit_code == 0
    assert "Dummy Pattern" in result.stdout

def test_cli_info(cli_runner, mock_registry):
    """Verifies that the 'nikame info' command works."""
    result = cli_runner.invoke(cli, ["info", "test.dummy", "--registry", str(mock_registry)])
    assert result.exit_code == 0
    assert "A dummy pattern for testing" in result.stdout

def test_cli_infra_docker(cli_runner, tmp_project):
    """Verifies that the 'nikame infra docker' command works."""
    result = cli_runner.invoke(cli, ["infra", "docker", "--path", str(tmp_project)])
    assert result.exit_code == 0
    assert "Created Dockerfile" in result.stdout
    assert (tmp_project / "Dockerfile").exists()
    assert (tmp_project / "docker-compose.yml").exists()

def test_cli_stub(cli_runner, tmp_path):
    """Verifies that the 'nikame stub' command works."""
    f = tmp_path / "test.py"
    f.write_text("class A: pass")
    
    result = cli_runner.invoke(cli, ["stub", str(f)])
    assert result.exit_code == 0
    assert "class A:" in result.stdout
