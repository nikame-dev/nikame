import shutil
import socket
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DoctorCheck:
    name: str
    status: bool
    version: str = ""
    message: str = ""


class DoctorEngine:
    """Engine for performing environment and project diagnostic checks."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

    def run_all(self) -> list[DoctorCheck]:
        """Executes all diagnostic checks."""
        checks = [
            self.check_python(),
            self.check_nikame(),
            self.check_ollama(),
            self.check_docker(),
            self.check_git(),
            self.check_project_config(),
            self.check_manifest(),
        ]
        return checks

    def check_python(self) -> DoctorCheck:
        import platform
        v = platform.python_version()
        return DoctorCheck("Python", sys.version_info >= (3, 10), version=v)

    def check_nikame(self) -> DoctorCheck:
        # Simplified for now
        return DoctorCheck("NIKAME", True, version="2.0.0a1")

    def check_ollama(self) -> DoctorCheck:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                connected = s.connect_ex(("127.0.0.1", 11434)) == 0
            if connected:
                return DoctorCheck("Ollama", True, message="running")
            return DoctorCheck("Ollama", False, message="not running")
        except Exception:
            return DoctorCheck("Ollama", False, message="error")

    def check_docker(self) -> DoctorCheck:
        docker_path = shutil.which("docker")
        if docker_path:
            # We could run 'docker version' but let's just check existence for now
            return DoctorCheck("Docker", True)
        return DoctorCheck("Docker", False, message="not found")

    def check_git(self) -> DoctorCheck:
        git_path = shutil.which("git")
        if git_path:
            return DoctorCheck("Git", True)
        return DoctorCheck("Git", False, message="not found")

    def check_project_config(self) -> DoctorCheck:
        config_path = self.project_root / "nikame.yaml"
        if config_path.exists():
            return DoctorCheck("Project Config", True, message="found")
        return DoctorCheck("Project Config", False, message="not found")

    def check_manifest(self) -> DoctorCheck:
        manifest_path = self.project_root / ".nikame" / "context.yaml"
        if manifest_path.exists():
            return DoctorCheck("Manifest", True, version="v2", message="found")
        return DoctorCheck("Manifest", False, message="not found")
