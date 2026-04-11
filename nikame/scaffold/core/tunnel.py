"""
nikame tunnel — ngrok integration layer.

Manages the lifecycle of uvicorn + ngrok tunnels:
  - Find free port
  - Start uvicorn subprocess
  - Wait for server readiness
  - Open ngrok tunnel
  - Display tunnel info
  - Graceful shutdown on Ctrl+C
"""
from __future__ import annotations

import asyncio
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from rich.console import Console

from nikame.scaffold.core.config import get_config

console = Console()


def find_free_port() -> int:
    """Find an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def wait_for_server(host: str, port: int, timeout: float = 15.0) -> bool:
    """
    Poll a local server until it responds to HTTP requests.

    Tries GET / and GET /health — whichever comes first.
    Returns True if server is up within timeout, False otherwise.
    """
    start = time.monotonic()
    url_base = f"http://{host}:{port}"

    while time.monotonic() - start < timeout:
        for path in ["/health", "/", "/docs"]:
            try:
                resp = httpx.get(f"{url_base}{path}", timeout=1.0)
                if resp.status_code < 500:
                    return True
            except (httpx.ConnectError, httpx.ReadError, httpx.TimeoutException):
                pass
        time.sleep(0.3)

    return False


def start_uvicorn_subprocess(
    app_module: str,
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    cwd: str | Path | None = None,
) -> subprocess.Popen:
    """
    Start uvicorn in a subprocess.

    Returns the Popen handle for lifecycle management.
    """
    cmd = [
        sys.executable, "-m", "uvicorn",
        app_module,
        "--host", host,
        "--port", str(port),
    ]
    if reload:
        cmd.append("--reload")

    env = os.environ.copy()
    # Ensure the cwd is on the Python path so imports work
    if cwd:
        python_path = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{cwd}:{python_path}" if python_path else str(cwd)

    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc


def open_ngrok_tunnel(port: int, auth_token: str | None = None) -> Any:
    """
    Open an ngrok tunnel to the specified local port.

    Uses pyngrok for cross-platform compatibility.
    Returns the ngrok tunnel object.
    """
    from pyngrok import ngrok, conf

    if auth_token:
        conf.get_default().auth_token = auth_token

    tunnel = ngrok.connect(port, "http")
    return tunnel


def close_ngrok_tunnel(tunnel: Any) -> None:
    """Close an ngrok tunnel."""
    from pyngrok import ngrok

    try:
        ngrok.disconnect(tunnel.public_url)
    except Exception:
        pass

    try:
        ngrok.kill()
    except Exception:
        pass


def generate_qr_code(url: str) -> str:
    """Generate a QR code as ANSI art for terminal display."""
    try:
        import qrcode
        from io import StringIO

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Generate ASCII art
        output = StringIO()
        qr.print_ascii(out=output, invert=True)
        return output.getvalue()
    except ImportError:
        return f"[QR code requires 'qrcode' package]\nURL: {url}"


def graceful_shutdown(proc: subprocess.Popen | None, tunnel: Any | None) -> None:
    """Clean shutdown of uvicorn subprocess and ngrok tunnel."""
    console.print("\n[yellow]Shutting down...[/yellow]")

    if tunnel:
        close_ngrok_tunnel(tunnel)
        console.print("  [green]✓[/green] ngrok tunnel closed")

    if proc and proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        console.print("  [green]✓[/green] uvicorn stopped")

    console.print("[green]Goodbye![/green]")
