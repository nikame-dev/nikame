"""nikame tunnel — View active Ngrok tunnels."""

from __future__ import annotations
import click
import requests
from nikame.utils.logger import console

@click.command()
@click.pass_context
def tunnel(ctx: click.Context) -> None:
    """View active Ngrok tunnel status."""
    try:
        response = requests.get("http://localhost:4040/api/tunnels", timeout=2)
        if response.status_code == 200:
            data = response.json()
            tunnels = data.get("tunnels", [])
            
            if not tunnels:
                console.print("[warning]No active tunnels found on the local ngrok agent.[/warning]")
                return
                
            console.print("\n[success]✨ Active Ngrok Tunnels:[/success]")
            for t in tunnels:
                public_url = t.get("public_url")
                local_addr = t.get("config", {}).get("addr")
                console.print(f"  [cyan]{public_url}[/cyan] -> {local_addr}")
            console.print("")
        else:
            console.print(f"[error]Failed to fetch tunnels: {response.status_code}[/error]")
            
    except requests.exceptions.ConnectionError:
        console.print("[warning]Ngrok agent API is not accessible at localhost:4040. Ensure the app is running in 'local' environment with the ngrok module enabled.[/warning]")
    except Exception as e:
        console.print(f"[error]Error checking tunnel: {e}[/error]")
