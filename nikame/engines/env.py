import re
from pathlib import Path


class EnvEngine:
    """Handles .env file management and secret detection."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.env_file = project_root / ".env"
        self.env_example_file = project_root / ".env.example"

    def add_variable(self, name: str, value: str, example: str | None = None) -> None:
        """Adds an environment variable to .env and .env.example."""
        self._append_to_file(self.env_file, f"{name}={value}")
        if example:
            self._append_to_file(self.env_example_file, f"{name}={example}")
        else:
            self._append_to_file(self.env_example_file, f"{name}=")

    def _append_to_file(self, file_path: Path, line: str) -> None:
        if not file_path.exists():
            file_path.write_text(f"{line}\n")
            return

        content = file_path.read_text()
        if line.split('=')[0] in content:
            return # Variable already exists, avoid duplicates
            
        if not content.endswith('\n'):
            line = f"\n{line}"
        file_path.write_text(content + f"{line}\n")

    def detect_secrets(self, content: str) -> list[str]:
        """Basic regex-based secret detection (to be replaced by better engine later)."""
        # Simplified patterns for common secrets
        patterns = [
            r'password\s*[:=]\s*["\']?([^"\'\s]{4,})["\']?',
            r'secret_key\s*[:=]\s*["\']?([^"\'\s]{16,})["\']?',
            r'api_key\s*[:=]\s*["\']?([^"\'\s]{16,})["\']?'
        ]
        found = []
        for p in patterns:
            matches = re.findall(p, content, re.IGNORECASE)
            found.extend(matches)
        return found
