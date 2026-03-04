"""Rich-based console and stdlib logging configuration for NIKAME."""

import logging
import sys

from rich.console import Console
from rich.theme import Theme

# NIKAME custom theme
_NIKAME_THEME = Theme(
    {
        "info": "cyan",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "module": "bold magenta",
        "path": "dim cyan",
        "key": "bold white",
    }
)

# Singleton console — import this everywhere for user-facing output.
# NEVER use print() anywhere in NIKAME.
console = Console(theme=_NIKAME_THEME, stderr=True)


def setup_logging(*, verbose: bool = False) -> None:
    """Configure stdlib logging for NIKAME internal debug logs.

    Args:
        verbose: If True, set level to DEBUG. Otherwise INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root = logging.getLogger("nikame")
    root.setLevel(level)
    root.addHandler(handler)
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced NIKAME logger.

    Args:
        name: Logger name (will be prefixed with 'nikame.').
    """
    return logging.getLogger(f"nikame.{name}")
