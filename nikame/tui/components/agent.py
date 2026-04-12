from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Markdown, Static


class ThoughtStream(VerticalScroll): # type: ignore[misc]
    """
    A scrollable container for agent thoughts and code blocks.
    Supports real-time streaming updates.
    """
    
    DEFAULT_CSS = """
        ThoughtStream {
            background: $panel;
            border: none;
        }
        
        .thought-text {
            color: $text-primary;
            margin-bottom: 1;
        }
        
        .agent-header {
            color: $accent;
            text-style: bold;
            margin-bottom: 1;
        }
    """

    def compose(self) -> ComposeResult:
        # Initial content
        yield Static("AI Reasoning Engine Online", classes="agent-header")
        yield Markdown("Waiting for user input...", id="main-markdown")

    async def update_markdown(self, content: str) -> None:
        """Updates the main markdown display."""
        markdown = self.query_one("#main-markdown", Markdown)
        await markdown.update(content)
        self.scroll_end(animate=False)


class ActionCard(Static): # type: ignore[misc]
    """
    A UI component for presenting a proposed plan with Accept/Reject buttons.
    """
    
    DEFAULT_CSS = """
        ActionCard {
            background: $surface;
            border: solid $accent;
            padding: 1;
            margin: 1;
            height: auto;
        }
        
        .action-title {
            color: $accent;
            text-style: bold;
        }
        
        .action-buttons {
            layout: horizontal;
            height: 3;
            margin-top: 1;
        }
        
        Button {
            width: 1fr;
            margin: 0 1;
        }
    """

    def __init__(self, title: str, summary: str) -> None:
        super().__init__()
        self.title_text = title
        self.summary_text = summary

    def compose(self) -> ComposeResult:
        from textual.widgets import Button, Label
        yield Label(f"[bold accent]{self.title_text}[/]")
        yield Label(self.summary_text)
        with VerticalScroll(): # Or Horizontal for buttons
            yield Button("Accept", variant="success", id="accept-btn")
            yield Button("Reject", variant="error", id="reject-btn")
