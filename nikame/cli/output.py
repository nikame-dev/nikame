from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme

# NIKAME Modernized Design System (Amber Core)
# Adapted from ui_ux.md specification
NIKAME_THEME = Theme({
    "accent": "#D4933A",      # Amber
    "text_primary": "#E8E0D0", # Off-white
    "text_secondary": "#8A8070", # Muted taupe
    "text_muted": "#524B40",   # Dark taupe
    "success": "#5A9E6F",
    "warning": "#C4933A",
    "danger": "#B85450",
    "section": "bold #D4933A",
})

console = Console(theme=NIKAME_THEME)


def print_header(title: str) -> None:
    """Prints a bold NIKAME section header."""
    console.print(f"\n[accent]⚡ NIKAME[/accent] [text_secondary]·[/text_secondary] [text_primary]{title}[/text_primary]")
    console.print("[text_muted]" + "─" * 60 + "[/text_muted]")


def print_section(title: str) -> None:
    """Prints a subsection divider."""
    console.print(f"\n[section]── {title} [/][text_muted]" + "─" * (56 - len(title)) + "[/text_muted]")


def print_info(message: str) -> None:
    """Prints a standard info message."""
    console.print(f"[text_secondary]info:[/] {message}")


def print_success(message: str) -> None:
    """Prints a success message with an icon."""
    console.print(f"[success]✓[/success] {message}")


def print_error(message: str) -> None:
    """Prints an error panel."""
    console.print(Panel(
        message,
        title="[danger]Error[/danger]",
        border_style="danger",
        padding=(1, 2)
    ))
