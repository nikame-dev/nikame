from typing import Any

from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    ContentSwitcher,
    Footer,
    Header,
    Input,
    Label,
    SelectionList,
    Static,
)
from textual.widgets.selection_list import Selection


class SidebarItem(Static):
    """A single item in the sidebar indicating step progress."""
    def __init__(self, label: str, step_id: str, **kwargs: Any) -> None:
        super().__init__(label, id=f"sidebar-{step_id}", **kwargs)
        self.step_id = step_id

class InitWizard(Screen[dict[str, Any] | None]):  # type: ignore[misc]
    """
    State-of-the-art multi-step setup wizard for NIKAME projects.
    """
    
    BINDINGS = [
        ("enter", "submit", "Next Step"),
        ("b", "back", "Previous Step"),
        ("escape", "cancel", "Cancel Setup"),
    ]

    CSS = """
        InitWizard {
            background: $background;
        }

        #wizard-grid {
            grid-size: 2 1;
            grid-columns: 28 1fr;
            height: 100%;
            border-top: tall $border;
        }

        #sidebar {
            background: $surface;
            border-right: tall $border;
            padding: 2 2;
        }

        .sidebar-title {
            color: $primary;
            text-style: bold;
            margin-bottom: 2;
        }

        SidebarItem {
            padding: 1 1;
            color: $text-secondary;
            border-left: thick transparent;
        }

        SidebarItem.active {
            color: $primary;
            background: $primary-darken-1;
            border-left: thick $primary;
            text-style: bold;
        }

        SidebarItem.completed {
            color: $success;
        }

        #content-area {
            padding: 2 4;
            height: 100%;
        }

        ContentSwitcher {
            height: 100%;
        }

        .step-container {
            height: 100%;
            color: $text-primary;
        }

        .step-header {
            margin-bottom: 2;
        }

        .step-title {
            color: $primary;
            text-style: bold underline;
        }

        .step-desc {
            color: $text-secondary;
            margin-bottom: 2;
        }

        Input {
            margin-bottom: 1;
            border: tall $border;
        }

        Input:focus {
            border: tall $primary;
        }

        SelectionList {
            height: 1fr;
            border: tall $border;
            margin-bottom: 1;
        }

        SelectionList:focus {
            border: tall $primary;
        }

        #summary-pane {
            background: $panel;
            padding: 1 2;
            border: double $primary;
            height: 1fr;
        }

        #nav-help {
            dock: bottom;
            height: 3;
            background: $surface;
            color: $text-muted;
            content-align: center middle;
        }
    """

    def __init__(self) -> None:
        super().__init__()
        self.step_index = 0
        self.steps = ["identity", "architecture", "infrastructure", "finalize"]
        self.data: dict[str, Any] = {
            "name": "my-nikame-app",
            "description": "A production-grade FastAPI service",
            "modules": ["database.postgres", "auth.jwt"],
            "profile": "local"
        }

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Grid(id="wizard-grid"):
            with Vertical(id="sidebar"):
                yield Label("NIKAME V2.0", classes="sidebar-title")
                yield SidebarItem("Identity", "identity", classes="active")
                yield SidebarItem("Architecture", "architecture")
                yield SidebarItem("Infrastructure", "infrastructure")
                yield SidebarItem("Finalize", "finalize")
            
            with Vertical(id="content-area"):
                with ContentSwitcher(initial="step-identity"):
                    # Step 1: Identity
                    with Vertical(id="step-identity", classes="step-container"):
                        yield Label("SYSTEM IDENTITY", classes="step-title")
                        yield Label("Define the core signature of your application.", classes="step-desc")
                        yield Input(placeholder="Project Name", id="proj-name", value=self.data["name"])
                        yield Input(placeholder="System Description", id="proj-desc", value=self.data["description"])

                    # Step 2: Architecture
                    with Vertical(id="step-architecture", classes="step-container"):
                        yield Label("SYSTEM ARCHITECTURE", classes="step-title")
                        yield Label("Select design patterns to weave into your codebase.", classes="step-desc")
                        yield SelectionList[str](
                            Selection("PostgreSQL (SQLAlchemy)", "database.postgres", True),
                            Selection("JWT Authentication", "auth.jwt", True),
                            Selection("Redis Cache Layer", "cache.redis", False),
                            Selection("Docker Ecosystem", "infra.docker", True),
                            id="module-selection"
                        )

                    # Step 3: Infrastructure
                    with Vertical(id="step-infrastructure", classes="step-container"):
                        yield Label("INFRASTRUCTURE PROFILE", classes="step-title")
                        yield Label("Select your target environment profile.", classes="step-desc")
                        yield SelectionList[str](
                            Selection("Local Development", "local", True),
                            Selection("Staging / QA", "staging", False),
                            Selection("Production Optimized", "production", False),
                            id="profile-selection"
                        )

                    # Step 4: Finalize
                    with Vertical(id="step-finalize", classes="step-container"):
                        yield Label("CONFIRM ARCHITECTURE", classes="step-title")
                        yield Label("Review your system specifications before generation.", classes="step-desc")
                        yield Static(id="summary-pane")

        yield Label("SPACE: Toggle  |  ENTER: Next  |  B: Back  |  ESC: Cancel", id="nav-help")
        yield Footer()

    def on_mount(self) -> None:
        """Set initial focus."""
        self.query_one("#proj-name").focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Progress when Enter is pressed in an Input."""
        self.action_submit()

    def action_submit(self) -> None:
        """Handle Enter key to progress."""
        current_step = self.steps[self.step_index]
        
        # Collect data from current step
        if current_step == "identity":
            self.data["name"] = self.query_one("#proj-name", Input).value
            self.data["description"] = self.query_one("#proj-desc", Input).value
        elif current_step == "architecture":
            self.data["modules"] = self.query_one("#module-selection", SelectionList).selected
        elif current_step == "infrastructure":
            selected = self.query_one("#profile-selection", SelectionList).selected
            self.data["profile"] = selected[0] if selected else "local"

        if self.step_index < len(self.steps) - 1:
            self.step_index += 1
            self.update_view()
        else:
            self.dismiss(self.data)

    def action_back(self) -> None:
        """Handle B key to go back."""
        if self.step_index > 0:
            self.step_index -= 1
            self.update_view()

    def action_cancel(self) -> None:
        """Handle ESC to cancel."""
        self.dismiss(None)

    def update_view(self) -> None:
        """Update the TUI state based on step index."""
        target_step = self.steps[self.step_index]
        
        # Switch content
        self.query_one(ContentSwitcher).current = f"step-{target_step}"
        
        # Update sidebar
        for i, step in enumerate(self.steps):
            item = self.query_one(f"#sidebar-{step}", SidebarItem)
            item.remove_class("active")
            item.remove_class("completed")
            
            if i == self.step_index:
                item.add_class("active")
            elif i < self.step_index:
                item.add_class("completed")

        # Focus management
        if target_step == "identity":
            self.query_one("#proj-name").focus()
        elif target_step == "architecture":
            self.query_one("#module-selection").focus()
        elif target_step == "infrastructure":
            self.query_one("#profile-selection").focus()
        elif target_step == "finalize":
            self.update_summary()

    def update_summary(self) -> None:
        """Populate the summary pane."""
        pane = self.query_one("#summary-pane", Static)
        output = f"[bold primary]PROPOSED SYSTEM ARCHITECTURE[/]\n\n"
        output += f"Project Name:     [accent]{self.data['name']}[/]\n"
        output += f"Description:      [text_secondary]{self.data['description']}[/]\n"
        output += f"Environment:      [success]{self.data['profile'].upper()}[/]\n\n"
        output += "[bold primary]SELECTED PATTERNS[/]\n"
        for mod in self.data["modules"]:
            output += f"  • {mod}\n"
        
        output += "\n\n[text_muted]Press ENTER to generate project files...[/]"
        pane.update(output)
