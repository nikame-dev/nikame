"""Secure credential storage for NIKAME.

Handles saving/loading GitHub OAuth tokens and other platform secrets
in ~/.nikame/credentials.json.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class CredentialManager:
    """Manages NIKAME user credentials.

    Stores data in ~/.nikame/credentials.json. In a production environment,
    this should use the system keyring (e.g., via the 'keyring' library),
    but for this implementation, we use a local JSON file with restricted
    permissions.
    """

    def __init__(self) -> None:
        self.config_dir = Path.home() / ".nikame"
        self.creds_file = self.config_dir / "credentials.json"

    def _ensure_config_dir(self) -> None:
        """Ensure the config directory exists with restricted permissions."""
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            # Restricted permissions (drwx------)
            os.chmod(self.config_dir, 0o700)

    def save_github_token(self, token: str, user_data: dict[str, Any] | None = None) -> None:
        """Save GitHub access token and optional user metadata.

        Args:
            token: GitHub Personal Access Token or OAuth token.
            user_data: Optional metadata (username, etc.).
        """
        self._ensure_config_dir()
        data = self.get_all_credentials()
        data["github"] = {
            "access_token": token,
            "user": user_data or {},
        }
        
        self.creds_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        # Restricted permissions (-rw-------)
        os.chmod(self.creds_file, 0o600)

    def get_github_token(self) -> str | None:
        """Retrieve the stored GitHub access token.

        Returns:
            The token string or None if not logged in.
        """
        data = self.get_all_credentials()
        return data.get("github", {}).get("access_token")

    def get_github_user(self) -> dict[str, Any] | None:
        """Retrieve the stored GitHub user metadata.

        Returns:
            User metadata dict or None.
        """
        data = self.get_all_credentials()
        return data.get("github", {}).get("user")

    def delete_github_credentials(self) -> None:
        """Clear GitHub credentials."""
        data = self.get_all_credentials()
        if "github" in data:
            del data["github"]
            self.creds_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_all_credentials(self) -> dict[str, Any]:
        """Read all credentials from the storage file.

        Returns:
            Dictionary of all stored credentials.
        """
        if not self.creds_file.exists():
            return {}
        try:
            return json.loads(self.creds_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}


# Global instance
credentials = CredentialManager()
