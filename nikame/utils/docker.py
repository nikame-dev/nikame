"""Docker utilities for NIKAME.

Handles port conflict detection and container lifecycle management.
"""

from __future__ import annotations

from typing import Any

import docker  # type: ignore[import-untyped]
import yaml


def find_conflicting_containers(compose_data: dict[str, Any]) -> list[Any]:
    """Find running containers that conflict with ports defined in compose_data.

    Args:
        compose_data: Parsed docker-compose.yml content.

    Returns:
        List of conflicting Docker container objects.
    """
    requested_ports: set[int] = set()
    
    services = compose_data.get("services", {})
    if not isinstance(services, dict):
        return []

    for service in services.values():
        ports = service.get("ports", [])
        if not isinstance(ports, list):
            continue
            
        for port_entry in ports:
            # Handle list of strings like ["8000:8000", "5432"]
            try:
                host_port_str = str(port_entry).split(":")[0]
                if host_port_str.isdigit():
                    requested_ports.add(int(host_port_str))
            except (ValueError, IndexError):
                continue

    if not requested_ports:
        return []

    client = docker.from_env()
    conflicting_containers = []
    
    # Get all running containers
    for container in client.containers.list():
        # Inspect port bindings
        ports_config = container.attrs.get("HostConfig", {}).get("PortBindings", {})
        if not ports_config:
            # Fallback to NetworkSettings if HostConfig is missing (rare)
            ports_config = container.attrs.get("NetworkSettings", {}).get("Ports", {})
            
        if not ports_config:
            continue
            
        is_conflicting = False
        for bindings in ports_config.values():
            if not bindings:
                continue
            for binding in bindings:
                host_port = binding.get("HostPort")
                if host_port and int(host_port) in requested_ports:
                    conflicting_containers.append(container)
                    is_conflicting = True
                    break
            if is_conflicting:
                break
                
    return conflicting_containers


def stop_containers(containers: list[Any]) -> None:
    """Stop a list of Docker containers."""
    for container in containers:
        container.stop()


def get_project_containers(project_name: str) -> list[Any]:
    """Get all containers belonging to a specific NIKAME project.
    
    Args:
        project_name: The NIKAME project name.
        
    Returns:
        List of Docker container objects.
    """
    client = docker.from_env()
    return client.containers.list(
        all=True,
        filters={"label": [f"com.docker.compose.project={project_name}"]}
    )


def get_container_logs(container: Any, tail: int = 20) -> str:
    """Get the last N lines of logs from a container.
    
    Args:
        container: Docker container object.
        tail: Number of lines to return.
        
    Returns:
        String containing the logs.
    """
    try:
        logs = container.logs(tail=tail).decode("utf-8")
        return logs
    except Exception as e:
        return f"Could not retrieve logs: {e}"
