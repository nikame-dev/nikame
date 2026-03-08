"""Template Registry Client (Mock & Remote)."""

import json
from pathlib import Path
from typing import Any
import yaml

from nikame.utils.logger import console

LOCAL_REGISTRY_DIR = Path("~/.nikame/registry").expanduser()

class RegistryClient:
    """Client for interacting with the Template Registry."""

    def __init__(self) -> None:
        self.local_dir = LOCAL_REGISTRY_DIR
        self.local_dir.mkdir(parents=True, exist_ok=True)
        self.remote_url = "http://localhost:8005"
        
        try:
            import requests
            r = requests.get(f"{self.remote_url}/health", timeout=1)
            self.use_remote = r.status_code == 200
        except Exception:
            self.use_remote = False
            
        if self.use_remote:
            console.print("[dim]🔗 Connected to remote Template Registry[/dim]")

    def search(self, query: str, tag: str | None = None, sort: str = "recent", verified_only: bool = False) -> list[dict[str, Any]]:
        """Search templates in the registry."""
        if self.use_remote:
            import requests
            params = {"sort_by": sort, "verified_only": verified_only}
            if query: params["q"] = query
            if tag: params["tag"] = tag
            try:
                r = requests.get(f"{self.remote_url}/templates", params=params)
                if r.status_code == 200:
                    return r.json()
            except Exception as e:
                console.print(f"[warning]Remote search failed: {e}. Falling back to local.[/warning]")
                
        results = []
        for file in self.local_dir.glob("*.yaml"):
            try:
                with open(file, "r") as f:
                    content = yaml.safe_load(f)
                    
                meta = content.get("registry_meta", {})
                
                # Filters
                if verified_only and not meta.get("verified", False):
                    continue
                if tag and tag not in meta.get("tags", []):
                    continue
                    
                # Search (name, description, tags)
                search_text = (content.get("name", "") + " " + content.get("description", "") + " " + " ".join(meta.get("tags", []))).lower()
                if query and query.lower() not in search_text:
                    continue
                    
                results.append({
                    "id": file.stem,
                    "name": content.get("name", "Unknown"),
                    "description": content.get("description", ""),
                    "tags": meta.get("tags", []),
                    "stars": meta.get("stars", 0),
                    "author": meta.get("author", "anonymous"),
                    "verified": meta.get("verified", False),
                    "version": content.get("version", "1.0"),
                    "raw": content
                })
            except Exception as e:
                console.print(f"[dim]Failed to read {file.name}: {e}[/dim]")
                
        # Sorting
        if sort == "stars":
            results.sort(key=lambda x: x["stars"], reverse=True)
        elif sort == "name":
            results.sort(key=lambda x: x["name"].lower())
        else: # recent (dummy implementation for mock)
            results.sort(key=lambda x: x["name"]) # Just sort by name for local mock
            
        return results

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        """Get full template by ID."""
        if self.use_remote:
            import requests
            try:
                r = requests.get(f"{self.remote_url}/templates/{template_id}")
                if r.status_code == 200:
                    data = r.json()
                    # Reconstruct structure expected by CLI
                    meta = {
                        "author": data.get("author", "anonymous"),
                        "stars": data.get("stars", 0),
                        "downloads": data.get("downloads", 0),
                        "verified": data.get("verified", False),
                        "tags": data.get("tags", [])
                    }
                    return {
                        "id": template_id,
                        "raw": data.get("raw_config", {}),
                        "meta": meta
                    }
            except Exception as e:
                console.print(f"[warning]Remote get failed: {e}. Falling back to local.[/warning]")
                
        file = self.local_dir / f"{template_id}.yaml"
        if not file.exists():
            return None
            
        with open(file, "r") as f:
            content = yaml.safe_load(f)
            return {
                "id": template_id,
                "raw": content,
                "meta": content.get("registry_meta", {})
            }

    def publish(self, template_id: str, content: dict[str, Any], meta: dict[str, Any]) -> str:
        """Publish a template to the registry."""
        if self.use_remote:
            import requests
            payload = {
                "id": template_id,
                "name": content.get("name", "Unknown"),
                "description": content.get("description", ""),
                "tags": meta.get("tags", []),
                "version": content.get("version", "1.0"),
                "raw_config": content,
                "author": meta.get("author", "anonymous")
            }
            try:
                r = requests.post(f"{self.remote_url}/templates", json=payload)
                if r.status_code == 201:
                    return f"{self.remote_url}/templates/{template_id}"
            except Exception as e:
                console.print(f"[warning]Remote publish failed: {e}. Falling back to local.[/warning]")
                
        file = self.local_dir / f"{template_id}.yaml"
        
        # Merge metadata for storage
        content["registry_meta"] = meta
        
        with open(file, "w") as f:
            yaml.dump(content, f, sort_keys=False)
            
        return f"local://{template_id}"

    def star(self, template_id: str) -> bool:
        """Star a template."""
        if self.use_remote:
            import requests
            try:
                r = requests.post(f"{self.remote_url}/templates/{template_id}/star")
                if r.status_code == 200:
                    return True
            except Exception as e:
                console.print(f"[warning]Remote star failed: {e}. Falling back to local.[/warning]")
                
        file = self.local_dir / f"{template_id}.yaml"
        if not file.exists():
            return False
            
        with open(file, "r") as f:
            content = yaml.safe_load(f)
            
        meta = content.setdefault("registry_meta", {})
        meta["stars"] = meta.get("stars", 0) + 1
        
        with open(file, "w") as f:
            yaml.dump(content, f, sort_keys=False)
            
        return True

    def unstar(self, template_id: str) -> bool:
        """Unstar a template."""
        if self.use_remote:
            import requests
            try:
                r = requests.post(f"{self.remote_url}/templates/{template_id}/unstar")
                if r.status_code == 200:
                    return True
            except Exception as e:
                console.print(f"[warning]Remote unstar failed: {e}. Falling back to local.[/warning]")
                
        file = self.local_dir / f"{template_id}.yaml"
        if not file.exists():
            return False
            
        with open(file, "r") as f:
            content = yaml.safe_load(f)
            
        meta = content.setdefault("registry_meta", {})
        meta["stars"] = max(0, meta.get("stars", 0) - 1)
        
        with open(file, "w") as f:
            yaml.dump(content, f, sort_keys=False)
            
        return True

    def get_user_templates(self, username: str) -> list[dict[str, Any]]:
        """Get templates by author."""
        if self.use_remote:
            import requests
            try:
                r = requests.get(f"{self.remote_url}/templates/mine", params={"author": username})
                if r.status_code == 200:
                    return r.json()
            except Exception as e:
                console.print(f"[warning]Remote get user templates failed: {e}. Falling back to local.[/warning]")
                
        results = []
        for file in self.local_dir.glob("*.yaml"):
            try:
                with open(file, "r") as f:
                    content = yaml.safe_load(f)
                meta = content.get("registry_meta", {})
                if meta.get("author") == username:
                    results.append({
                        "id": file.stem,
                        "name": content.get("name", "Unknown"),
                        "stars": meta.get("stars", 0),
                        "downloads": meta.get("downloads", 0),
                        "verified": meta.get("verified", False)
                    })
            except Exception:
                pass
        return results

    def verify(self, template_id: str) -> bool:
        """Mark a template as verified."""
        file = self.local_dir / f"{template_id}.yaml"
        if not file.exists():
            return False
            
        with open(file, "r") as f:
            content = yaml.safe_load(f)
            
        meta = content.setdefault("registry_meta", {})
        meta["verified"] = True
        
        with open(file, "w") as f:
            yaml.dump(content, f, sort_keys=False)
            
        return True
