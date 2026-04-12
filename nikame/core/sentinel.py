import traceback
import sys
from pathlib import Path
from typing import Callable, Any
from functools import wraps
from rich.console import Console

console = Console()

class Sentinel:
    """The Global Error Catch and Roadmap Generator."""
    def __init__(self, root_dir: Path = Path(".")):
        self.root_dir = root_dir
        self.tasks_file = self.root_dir / "tasks.md"

    def _append_task(self, error_msg: str, tb_str: str):
        content = ""
        if self.tasks_file.exists():
            content = self.tasks_file.read_text()
        else:
            content = "# 🛡️ NIKAME Action Roadmap\n\n"

        task_id = len(content.split("- [ ] Task ")) + 1
        
        # Super simple logic-based suggestion
        suggestion = "Use 'nikame agent fix --task {}' to resolve this issue.".format(task_id)
        if "Port" in error_msg:
            suggestion = "Resolve port conflict in nikame.yaml or explicitly state logical DB indexes (e.g. DB 1)."
        elif "No such file" in error_msg:
            suggestion = "Initialize the missing file or run 'nikame init' to generate base infrastructure."
            
        new_task = f"- [ ] Task {task_id}: **Error:** `{error_msg}`\n  - **Suggestion:** {suggestion}\n  - **Details:** Found in execution.\n<details>\n<summary>Traceback</summary>\n\n```python\n{tb_str}\n```\n</details>\n\n"
        
        self.tasks_file.write_text(content + new_task)
        return task_id

    def catch(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                task_id = self._append_task(str(e), traceback.format_exc())
                console.print(f"[bold red]Sentinel Blocked Execution[/bold red]")
                console.print(f"Exception: {str(e)}")
                console.print(f"[yellow]View tasks.md for details. Run 'nikame agent fix --task {task_id}' to self-heal.[/yellow]")
                sys.exit(1)
        return wrapper

_sentinel = None
def get_sentinel() -> Sentinel:
    global _sentinel
    if not _sentinel:
        _sentinel = Sentinel()
    return _sentinel
