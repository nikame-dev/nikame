from typing import Any
from textual.app import App
from textual.screen import Screen
from textual.widgets import Label
from rich.console import Console

console = Console()

class FinishScreen(Screen[dict[str, Any]]):
    def compose(self):
        yield Label("Press Enter to finish")
    def on_key(self, event):
        if event.key == "enter":
            self.dismiss({"name": "test"})

class TestApp(App[dict[str, Any]]):
    def on_mount(self):
        self.push_screen(FinishScreen())

if __name__ == "__main__":
    app = TestApp()
    result = app.run()
    console.print(f"Result: {result}")
