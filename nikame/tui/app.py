from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from .theme import get_css_variables_str


class NikameApp(App[None]): # type: ignore[misc]
    """
    The primary NIKAME application.
    Orchestrates screens and global state.
    """
    
    TITLE = "⚡ NIKAME"
    SUB_TITLE = "Autonomous Systems Orchestrator"
    
    CSS = get_css_variables_str() + """
        * {
            transition: background 200ms, color 200ms;
        }

        Screen {
            background: $background;
        }
        
        Header {
            background: $surface;
            color: $primary;
            text-style: bold;
            border-bottom: tall $border;
        }
        
        Footer {
            background: $surface;
            color: $text-secondary;
            border-top: tall $border;
        }
        
        Footer > .footer--key {
            color: $primary;
            background: $primary-darken-1;
            text-style: bold;
        }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("ctrl+r", "rollback", "Rollback", show=True),
    ]

    def __init__(self, project_root: Path | None = None) -> None:
        super().__init__()
        self.project_root = project_root or Path.cwd()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        # Main content will be dynamically loaded via screens
        yield Footer()

    async def on_mount(self) -> None:
        # Push the agent screen as default
        from .screens.agent import AgentScreen
        await self.push_screen(AgentScreen(self.project_root))

    def action_rollback(self) -> None:
        """Placeholder for global rollback action."""
        # This will eventually push a RollbackDialog
        pass


if __name__ == "__main__":
    app = NikameApp()
    app.run()
