from rich.console import Console
from rich.theme import Theme

custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "danger": "bold red",
    "success": "bold green"
})

console = Console(theme=custom_theme)

def print_info(text: str) -> None:
    console.print(f"[info]ℹ[/info] {text}")

def print_success(text: str) -> None:
    console.print(f"[success]✓[/success] {text}")

def print_warning(text: str) -> None:
    console.print(f"[warning]⚠[/warning] {text}")

def print_error(text: str) -> None:
    console.print(f"[danger]✘[/danger] {text}")
