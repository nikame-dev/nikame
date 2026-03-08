"""Docker Compose generator.

Collects compose_spec() from all resolved Blueprint modules,
merges services, volumes, and networks into a single valid
docker-compose.yml output.
"""

from __future__ import annotations

from typing import Any

from nikame.blueprint.engine import Blueprint
from nikame.utils.logger import get_logger

_log = get_logger("composers.docker_compose")


def generate_compose(blueprint: Blueprint) -> dict[str, Any]:
    """Merge all module compose_spec() outputs into a full docker-compose.yml.

    Args:
        blueprint: Resolved Blueprint with instantiated modules.

    Returns:
        Complete docker-compose.yml as a dict (ready for YAML serialization).
    """
    services: dict[str, Any] = {}
    volumes: dict[str, Any] = {}
    networks: dict[str, Any] = {
        f"{blueprint.project_name}_frontend": {"driver": "bridge"},
        f"{blueprint.project_name}_backend": {"driver": "bridge"},
        f"{blueprint.project_name}_data": {"driver": "bridge", "internal": True},
        f"{blueprint.project_name}_network": {"driver": "bridge"},
    }

    for module in blueprint.modules:
        spec = module.compose_spec()
        _log.debug("Merging compose_spec from module: %s", module.NAME)

        for service_name, service_config in spec.items():
            if service_name in services:
                _log.warning(
                    "Service name collision: '%s' (module: %s overwrites previous)",
                    service_name,
                    module.NAME,
                )
            
            # Apply default log rotation (Item 12: Simplified log aggregation)
            if "logging" not in service_config:
                service_config["logging"] = {
                    "driver": "json-file",
                    "options": {
                        "max-size": "10m",
                        "max-file": "3"
                    }
                }
            
            services[service_name] = service_config

            # Extract and register named volumes
            for vol in service_config.get("volumes", []):
                if isinstance(vol, str) and ":" in vol:
                    vol_name = vol.split(":")[0]
                    # Named volumes don't start with . or /
                    if not vol_name.startswith((".", "/", "$")):
                        volumes[vol_name] = None

    compose: dict[str, Any] = {
        "services": services,
    }

    if volumes:
        compose["volumes"] = {name: {} for name in sorted(volumes)}

    if networks:
        compose["networks"] = networks

    _log.debug(
        "Composed %d services, %d volumes, %d networks",
        len(services),
        len(volumes),
        len(networks),
    )

    return compose
