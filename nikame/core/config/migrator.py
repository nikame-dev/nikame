from rich.console import Console
from rich.prompt import Confirm
from typing import Any

console = Console()

def migrate_config(raw: dict[str, Any], old_version: str) -> dict[str, Any]:
    if str(old_version) in ("1.0", "1.x", "1", "1.1", "1.2", "1.3"):
        console.print(f"[yellow]Migrating config from v{old_version} to v2.0...[/yellow]")
        new_raw = {}
        new_raw["version"] = "2.0"
        new_raw["name"] = raw.get("name", "nikame-project")
        new_raw["description"] = raw.get("description")
        
        modules = []
        if "api" in raw and raw["api"].get("framework"):
            modules.append(f"api.{raw['api']['framework']}")
            
        for db, _ in raw.get("databases", {}).items():
            modules.append(f"database.{db}")
            
        if "cache" in raw and raw["cache"].get("provider"):
            modules.append(f"cache.{raw['cache']['provider']}")
            
        for msg, _ in raw.get("messaging", {}).items():
            modules.append(f"messaging.{msg}")
            
        if "storage" in raw and raw["storage"].get("provider"):
            modules.append(f"storage.{raw['storage']['provider']}")
            
        new_raw["modules"] = modules
        new_raw["features"] = []
        
        env_dict = raw.get("environment", {})
        new_raw["environment"] = {
            "target": env_dict.get("target", "local"),
            "resource_tier": "medium",
            "domain": None
        }
        
        new_raw["copilot"] = {
            "provider": "ollama",
            "model": "qwen2.5-coder:7b",
            "temperature": 0.2,
            "max_context_tokens": 8192
        }
        
        obs = raw.get("observability", {})
        new_raw["observability"] = {
            "metrics": bool(obs.get("metrics")),
            "tracing": bool(obs.get("traces")),
            "logging": obs.get("logging", "stdout")
        }
        
        return new_raw
    
    raise Exception(f"Unsupported config version: {old_version}")
