from datetime import UTC, datetime
from typing import Any

# Actually it's better to fetch nikame version properly, but we'll hardcode 2.0 for now
NIKAME_VERSION = "2.0.0"

def migrate_manifest(raw: dict[str, Any], old_version: str) -> dict[str, Any]:
    """Migrates a manifest from older versions to V2."""
    if old_version in ("1", "1.0"):
        new_raw: dict[str, Any] = {}
        new_raw["manifest_version"] = "2"
        new_raw["nikame_version"] = raw.get("nikame_version", NIKAME_VERSION)
        new_raw["project_name"] = raw.get("project_name", "migrated-project")
        new_raw["created_at"] = datetime.now(tz=UTC).isoformat()
        new_raw["patterns_applied"] = []
        
        # In v1 patterns might be just list of strings or simpler structures
        old_patterns = raw.get("patterns_applied", [])
        for p in old_patterns:
            if isinstance(p, dict):
                new_raw["patterns_applied"].append({
                    "id": p.get("id", "unknown"),
                    "version": p.get("version", "1.0"),
                    "applied_at": datetime.now(tz=UTC).isoformat(),
                    "files_created": [],
                    "files_modified": [],
                    "env_vars_added": []
                })
        
        new_raw["ports_allocated"] = []
        old_ports = raw.get("ports_allocated", {})
        if isinstance(old_ports, dict):
            for service, port in old_ports.items():
                new_raw["ports_allocated"].append({
                    "service": service,
                    "port": int(port),
                    "protocol": "tcp"
                })
        
        new_raw["env_vars"] = []
        new_raw["last_verified"] = None
        new_raw["verification_passed" ] = None
        return new_raw
    raise Exception(f"Unsupported manifest version: {old_version}")
