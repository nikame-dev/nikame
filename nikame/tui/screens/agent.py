from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DirectoryTree, Static

from ..components.agent import ThoughtStream


class AgentScreen(Screen[None]): # type: ignore[misc]
    """
    The primary agent execution screen.
    Layout: 18% (File Tree) | 50% (Agent Stream) | 32% (Actions/Status)
    """
    
    CSS = """
        AgentScreen {
            layout: horizontal;
        }
        
        #left-panel {
            width: 18%;
            border-right: tall $primary-darken-1;
            background: $background;
        }
        
        #middle-panel {
            width: 50%;
            background: $panel;
        }
        
        #right-panel {
            width: 32%;
            border-left: tall $primary-darken-1;
            background: $background;
        }
        
        .panel-header {
            width: 100%;
            height: 1;
            background: $primary-darken-1;
            color: $text-primary;
            text-align: center;
            text-style: bold;
        }
        
        DirectoryTree {
            background: $background;
            color: $text-secondary;
            border: none;
        }
        
        ThoughtStream {
            padding: 1 2;
        }
        
        .status-card {
            margin: 1 2;
            padding: 1;
            border: solid $primary-darken-1;
            background: $surface;
        }
        
        .label-value {
            color: $text-primary;
        }
        
        .label-key {
            color: $accent;
            text-style: bold;
        }
    """

    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = project_root

    def compose(self) -> ComposeResult:
        # Left Panel: File Tree
        with Vertical(id="left-panel"):
            yield Static(" EXPLORER ", classes="panel-header")
            yield DirectoryTree(str(self.project_root))

        # Middle Panel: Agent Reasoning & Code
        with Vertical(id="middle-panel"):
            yield Static(" AGENT CONSOLE ", classes="panel-header")
            yield ThoughtStream(id="agent-thought-stream")

        # Right Panel: Actions & Health
        with Vertical(id="right-panel"):
            yield Static(" SYSTEM STATUS ", classes="panel-header")
            with Vertical(classes="status-card"):
                yield Static("[bold accent]Project:[/] [text_primary]nikame-v2[/]")
                yield Static("[bold accent]Context:[/] [text_primary]4.2k tokens[/]")
                yield Static("[bold accent]LLM:[/] [text_primary]Ollama (qwen2.5-coder)[/]")
                yield Static("[bold accent]Health:[/] [success]✓ OK[/]")
            
            yield Static(" PROPOSED PLAN ", classes="panel-header")
            yield Static("No active plan. Waiting for task...", classes="status-card", id="plan-preview")
