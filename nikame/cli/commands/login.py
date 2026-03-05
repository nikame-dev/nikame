"""GitHub login command for NIKAME.

Handles OAuth2 flow with a local callback server on port 9876.
"""

from __future__ import annotations

import http.server
import socketserver
import urllib.parse
import webbrowser
from typing import Any

import click
import httpx

from nikame.utils.auth import credentials
from nikame.utils.github_client import GitHubClient
from nikame.utils.logger import console

# NIKAME GitHub OAuth App Credentials (placeholders for now)
GITHUB_CLIENT_ID = "CHANGEME_CLIENT_ID"
GITHUB_CLIENT_SECRET = "CHANGEME_CLIENT_SECRET"
CALLBACK_PORT = 9876
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """Handles the GitHub OAuth callback."""

    def do_GET(self) -> None:
        """Process the redirect from GitHub."""
        parsed_path = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed_path.query)

        if "code" in params:
            self.server.auth_code = params["code"][0]
            self._send_response("Authentication successful! You can close this tab.")
        else:
            self._send_response("Authentication failed. Please check the CLI output.")

    def _send_response(self, message: str) -> None:
        """Send a simple HTML response."""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        html = f"<html><body><h1>{message}</h1></body></html>"
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, log_format: str, *args: Any) -> None:
        """Silence logs."""
        pass


@click.command()
def login() -> None:
    """Authenticate with GitHub to enable repository automation."""
    console.print("[info]Starting GitHub authentication...[/info]")

    # 1. Generate Auth URL
    scopes = "repo workflow admin:org"
    auth_url = (
        f"https://github.com/login/oauth/authorize?"
        f"client_id={GITHUB_CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"scope={scopes}"
    )

    # 2. Start local callback server
    handler = OAuthCallbackHandler
    with socketserver.TCPServer(("", CALLBACK_PORT), handler) as httpd:
        httpd.auth_code = None
        console.print(f"[success]Opening browser at: {auth_url}[/success]")
        webbrowser.open(auth_url)

        # Wait for callback
        console.print("[info]Waiting for GitHub authorization...[/info]")
        httpd.handle_request()

        if not httpd.auth_code:
            console.print("[error]Failed to receive authentication code.[/error]")
            raise click.Abort()

        # 3. Exchange code for token
        console.print("[info]Exchanging code for access token...[/info]")
        resp = httpx.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": httpd.auth_code,
                "redirect_uri": REDIRECT_URI,
            },
        )
        data = resp.json()
        token = data.get("access_token")

        if not token:
            console.print(f"[error]Authentication failed: {data.get('error_description', 'Unknown error')}[/error]")
            raise click.Abort()

        # 4. Fetch user data and save
        client = GitHubClient(token)
        try:
            import anyio
            user = anyio.run(client.get_user)
            repo_count = anyio.run(client.get_repo_count)

            credentials.save_github_token(token, user_data=user)

            console.print(f"\n[success]✨ Successfully logged in as: [bold]{user.get('login')}[/bold][/success]")
            console.print(f"  Accessible repositories: {repo_count}")
        except Exception as exc:
            console.print(f"[error]Failed to finalize login: {exc}[/error]")
            raise click.Abort()


@click.command()
def logout() -> None:
    """Clear GitHub credentials from your machine."""
    user = credentials.get_github_user()
    if user:
        console.print(f"[info]Logging out [bold]{user.get('login')}[/bold]...[/info]")
        credentials.delete_github_credentials()
        console.print("[success]✓ Successfully logged out.[/success]")
    else:
        console.print("[info]You are not currently logged in.[/info]")


@click.command()
def whoami() -> None:
    """Show the currently logged in GitHub account."""
    user = credentials.get_github_user()
    if user:
        console.print(f"[info]Logged in as: [bold]{user.get('login')}[/bold][/info]")
        console.print("  Token source: [dim]~/.nikame/credentials.json[/dim]")
    else:
        console.print("[info]You are not logged in. Run [bold]nikame login[/bold] to authenticate.[/info]")
