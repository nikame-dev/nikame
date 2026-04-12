
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    ContentSwitcher,
    Input,
    Label,
    SelectionList,
    Static,
)
from textual.widgets.selection_list import Selection


class InitWizard(Screen[dict[str, Any] | None]):  # type: ignore[misc]
    """
    Step-by-step TUI wizard for project initialization.
    """
    
    CSS = """
        InitWizard {
            align: center middle;
            background: $background;
        }
        
        #wizard-container {
            width: 60;
            height: auto;
            border: thick $primary;
            background: $surface;
            padding: 1 2;
        }
        
        .wizard-step {
            display: none;
            height: auto;
        }
        
        .visible {
            display: block;
        }
        
        .step-title {
            text-align: center;
            color: $accent;
            text-style: bold;
            margin-bottom: 1;
        }
        
        .step-description {
            text-align: center;
            color: $text-secondary;
            margin-bottom: 2;
        }
        
        Input {
            margin-bottom: 1;
            border: tall $accent;
        }
        
        SelectionList {
            height: 8;
            border: tall $primary-darken-1;
            margin-bottom: 1;
        }
        
        #nav-buttons {
            layout: horizontal;
            height: 3;
            align: center middle;
            margin-top: 1;
        }
        
        Button {
            margin: 0 1;
        }
    """

    def __init__(self) -> None:
        super().__init__()
        self.step_index = 0
        self.total_steps = 3
        self.data = {
            "name": "my-nikame-app",
            "description": "A production-grade FastAPI service",
            "modules": []
        }

    def compose(self) -> ComposeResult:
        with Vertical(id="wizard-container"):
            with ContentSwitcher(initial="step-info"):
                # Step 1: Basic Info
                with Vertical(id="step-info", classes="wizard-step visible"):
                    yield Label("STEP 1: PROJECT INFO", classes="step-title")
                    yield Label("Define your system identity.", classes="step-description")
                    yield Input(placeholder="Project Name", id="project-name", value=str(self.data["name"]))
                    yield Input(placeholder="Description", id="project-desc", value=str(self.data["description"]))

                # Step 2: Feature Selection
                with Vertical(id="step-patterns", classes="wizard-step"):
                    yield Label("STEP 2: FEATURE REGISTRY", classes="step-title")
                    yield Label("Select core system patterns to inject.", classes="step-description")
                    yield SelectionList[str](
                        Selection("PostgreSQL Database", "database.postgres", True),
                        Selection("JWT Authentication", "auth.jwt", True),
                        Selection("Redis Cache", "cache.redis", False),
                        Selection("Docker Infrastructure", "infra.docker", True),
                        id="pattern-selection"
                    )

                # Step 3: Finalize
                with Vertical(id="step-finalize", classes="wizard-step"):
                    yield Label("STEP 3: FINALIZE", classes="step-title")
                    yield Label("Ready to architect your system?", classes="step-description")
                    yield Static(id="summary-text", classes="step-description")

            with Horizontal(id="nav-buttons"):
                yield Button("Back", id="btn-back", variant="default")
                yield Button("Next", id="btn-next", variant="primary")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-next":
            if self.step_index < self.total_steps - 1:
                await self.next_step()
            else:
                await self.finish()
        elif event.button.id == "btn-back":
            if self.step_index > 0:
                await self.prev_step()

    async def next_step(self) -> None:
        self.step_index += 1
        switcher = self.query_one(ContentSwitcher)
        
        if self.step_index == 1:
            self.data["name"] = self.query_one("#project-name", Input).value
            self.data["description"] = self.query_one("#project-desc", Input).value
            switcher.current = "step-patterns"
        elif self.step_index == 2:
            selection = self.query_one("#pattern-selection", SelectionList)
            self.data["modules"] = selection.selected
            self.update_summary()
            switcher.current = "step-finalize"
            self.query_one("#btn-next", Button).label = "Finish"

    async def prev_step(self) -> None:
        self.step_index -= 1
        switcher = self.query_one(ContentSwitcher)
        self.query_one("#btn-next", Button).label = "Next"
        
        if self.step_index == 0:
            switcher.current = "step-info"
        elif self.step_index == 1:
            switcher.current = "step-patterns"

    def update_summary(self) -> None:
        summary = self.query_one("#summary-text", Static)
        text = f"Project: [bold accent]{self.data['name']}[/]\n"
        text += f"Modules: [bold accent]{', '.join(self.data['modules'])}[/]\n\n"
        text += "Files will be generated in current directory."
        summary.update(text)

    async def finish(self) -> None:
        self.dismiss(self.data)
