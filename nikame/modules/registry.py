"""Module auto-discovery and registry.

Scans nikame/modules/ subdirectories, imports all BaseModule subclasses,
and registers them by NAME for lookup during blueprint resolution.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from nikame.modules.base import BaseModule
from nikame.utils.logger import get_logger

_log = get_logger("modules.registry")

# Global registry: module NAME → module class
_MODULE_REGISTRY: dict[str, type[BaseModule]] = {}


def register_module(module_cls: type[BaseModule]) -> None:
    """Register a module class in the global registry.

    Args:
        module_cls: A BaseModule subclass to register.
    """
    name = module_cls.NAME
    if name in _MODULE_REGISTRY:
        if _MODULE_REGISTRY[name] is module_cls:
            return  # Already registered identically, ignore silently
        _log.warning(
            "Module '%s' already registered (existing: %s, new: %s). Overwriting.",
            name,
            _MODULE_REGISTRY[name].__name__,
            module_cls.__name__,
        )
    _MODULE_REGISTRY[name] = module_cls
    _log.debug("Registered module: %s (%s)", name, module_cls.__name__)


def get_module_class(name: str) -> type[BaseModule] | None:
    """Look up a module class by NAME.

    Args:
        name: Module NAME (e.g., "postgres", "fastapi").

    Returns:
        The module class, or None if not found.
    """
    return _MODULE_REGISTRY.get(name)


def get_all_modules() -> dict[str, type[BaseModule]]:
    """Return a copy of the full module registry.

    Returns:
        Dict of module NAME → module class.
    """
    return dict(_MODULE_REGISTRY)


def discover_modules() -> None:
    """Auto-discover and register all modules in nikame/modules/.

    Walks all subpackages under nikame.modules, imports each module
    file, and registers any BaseModule subclasses found.
    """
    import nikame.modules as modules_pkg

    package_path = modules_pkg.__path__
    package_name = modules_pkg.__name__

    for importer, modname, ispkg in pkgutil.walk_packages(
        package_path, prefix=f"{package_name}."
    ):
        # Skip __init__, base, and registry modules
        short_name = modname.split(".")[-1]
        if short_name in ("__init__", "base", "registry"):
            continue

        try:
            module = importlib.import_module(modname)
        except Exception:
            _log.warning("Failed to import module: %s", modname, exc_info=True)
            continue

        # Find all BaseModule subclasses in this module
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseModule)
                and attr is not BaseModule
                and hasattr(attr, "NAME")
                and isinstance(getattr(attr, "NAME", None), str)
            ):
                register_module(attr)

    _log.debug("Discovery complete: %d modules registered", len(_MODULE_REGISTRY))


def _resolve_module_mapping(active_sections: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Map active config sections to module NAMEs and their configs.

    This is the bridge between nikame.yaml sections and module instances.

    Args:
        active_sections: Extracted config sections with their data.

    Returns:
        Dict of module NAME → config dict for instantiation.
    """
    return active_sections
