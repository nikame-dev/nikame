"""GitHub API client for NIKAME automation.

Handles repo creation, secret injection, and user metadata fetching.
"""

from __future__ import annotations

import base64
from typing import Any

import httpx
# Note: In a real environment, we'd use 'pynacl' for Libsodium encryption
# required by GitHub Secrets API. We will implement the wrapper here.
try:
    from nacl import encoding, public  # type: ignore
    HAS_NACL = True
except ImportError:
    HAS_NACL = False

from nikame.exceptions import NikameError


class GitHubClient:
    """Helper for NIKAME's GitHub platform integrations."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str) -> None:
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    async def get_user(self) -> dict[str, Any]:
        """Fetch current authenticated user data."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/user", headers=self.headers)
            if resp.status_code != 200:
                raise NikameError(f"GitHub identity check failed: {resp.text}")
            return resp.json()

    async def get_user_orgs(self) -> list[dict[str, Any]]:
        """List organizations the user belongs to."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/user/orgs", headers=self.headers)
            if resp.status_code == 401:
                raise NikameError("GitHub token expired or invalid. Please run 'nikame login'.")
            if resp.status_code != 200:
                raise NikameError(f"Failed to fetch organizations: {resp.text}")
            return resp.json()

    async def create_repo(
        self, name: str, description: str, private: bool = True, org: str | None = None
    ) -> dict[str, Any]:
        """Create a new repository (personal or org)."""
        url = f"{self.BASE_URL}/user/repos" if not org else f"{self.BASE_URL}/orgs/{org}/repos"
        async with httpx.AsyncClient() as client:
            payload = {
                "name": name,
                "description": description,
                "private": private,
                "auto_init": False,
            }
            resp = await client.post(url, headers=self.headers, json=payload)
            if resp.status_code == 422:
                raise NikameError(f"Repository '{name}' already exists.")
            if resp.status_code != 201:
                raise NikameError(f"Failed to create GitHub repo: {resp.text}")
            return resp.json()

    async def get_secret(self, owner: str, repo: str, secret_name: str) -> bool:
        """Check if a secret already exists in the repo."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/actions/secrets/{secret_name}",
                headers=self.headers,
            )
            return resp.status_code == 200

    async def set_secret(self, owner: str, repo: str, secret_name: str, secret_value: str) -> bool:
        """Inject a secret into the repository. Returns True if successful."""
        if not HAS_NACL:
            raise NikameError("PyNaCl is required for GitHub Secret encryption. Run: pip install pynacl")

        # GitHub Secrets limit is 64KB
        if len(secret_value.encode("utf-8")) > 65535:
            return False

        # 1. Get public key
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/actions/secrets/public-key",
                headers=self.headers,
            )
            if resp.status_code != 200:
                raise NikameError(f"Failed to get repo public key: {resp.text}")
            key_data = resp.json()
            key_id = key_data["key_id"]
            public_key = key_data["key"]

        # 2. Encrypt and set
        encrypted_value = self._encrypt_secret(public_key, secret_value)
        async with httpx.AsyncClient() as client:
            payload = {"encrypted_value": encrypted_value, "key_id": key_id}
            resp = await client.put(
                f"{self.BASE_URL}/repos/{owner}/{repo}/actions/secrets/{secret_name}",
                headers=self.headers,
                json=payload,
            )
            return resp.status_code in (201, 204)

    async def list_secrets(self, owner: str, repo: str) -> list[str]:
        """List current secret names in the repository."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/actions/secrets",
                headers=self.headers,
            )
            if resp.status_code != 200:
                return []
            return [s["name"] for s in resp.json().get("secrets", [])]

    def _encrypt_secret(self, public_key: str, secret_value: str) -> str:
        """Encrypt a secret using Libsodium to satisfy GitHub's API requirement."""
        public_key_bytes = base64.b64decode(public_key)
        sealed_box = public.SealedBox(public.PublicKey(public_key_bytes))
        encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
        return base64.b64encode(encrypted).decode("utf-8")
