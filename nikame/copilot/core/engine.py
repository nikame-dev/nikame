import asyncio
import re
import subprocess
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncIterator
import click
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

from nikame.copilot.core.ollama import OllamaClient
from nikame.copilot.core.context import CopilotContext
from nikame.scaffold.core.scaffolder import get_scaffolder
from nikame.scaffold.core.registry import get_registry
from nikame.copilot.utils import FileManager
from nikame.copilot.core.integrity import IntegrityEngine

class CopilotEngine:
    def __init__(self, model_name: str, mode: str = "fast"):
        self.model_name = model_name
        self.mode = mode
        self.client = OllamaClient()
        self.context = CopilotContext()
        self.file_manager = FileManager(Path("."))
        self.integrity = IntegrityEngine(Path("."))
        self.history: List[Dict[str, str]] = []
        self.console = Console()

    async def initialize(self):
        registry = get_registry()
        system_prompt = self.context.build_system_prompt(registry.all(), mode=self.mode)
        self.history.append({"role": "system", "content": system_prompt})

    async def chat_stream(self, user_input: str) -> AsyncIterator[str]:
        self.history.append({"role": "user", "content": user_input})
        try:
            full_response = ""
            async for token in self.client.chat_stream(
                model=self.model_name,
                messages=self.history,
                options={"num_ctx": 16384 if self.mode == "planning" else 8192, "temperature": 0.2}
            ):
                full_response += token
                yield token

            # After stream completes, execute actions and record history
            self.history.append({"role": "assistant", "content": full_response})
            feedback = await self._execute_actions(full_response)
            if feedback:
                yield f"\n\n[dim]Feedback: {feedback}[/dim]"
        except Exception as e:
            yield f"\n[red]Error: {str(e)}[/red]"

    async def _execute_actions(self, text: str) -> str:
        feedback = []
        is_fast = self.mode == "fast"

        # 1. SCAFFOLD
        for slug in re.findall(r"\[SCAFFOLD:\s*([^\]]+)\]", text):
            slug = slug.strip()
            self.console.print(f"[cyan]✨ Action: nikame scaffold add {slug}[/cyan]")
            if is_fast or click.confirm(f"Execute scaffold for {slug}?"):
                try:
                    get_scaffolder().scaffold(slug, Path("."))
                    feedback.append(f"Scaffold {slug} success.")
                except Exception as e:
                    feedback.append(f"Scaffold {slug} error: {str(e)}")

        # 2. WRITE
        for match in re.finditer(r"\[WRITE:\s*([^\]]+)\]\s*```[a-zA-Z0-9_\-\+]*\s*\n(.*?)(\n```|\Z)", text, re.DOTALL):
            target, content = Path(match.group(1).strip()), match.group(2)
            self.console.print(Panel(f"Action: Writing to {target}", border_style="yellow"))
            if is_fast or click.confirm(f"Commit changes to {target}?"):
                self.file_manager.create_backup(target)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
                feedback.append(f"Write {target} success.")

        # 3. COMMAND
        for cmd in re.findall(r"\[COMMAND:\s*([^\]]+)\]", text):
            self.console.print(f"[bold yellow]⚡ Command:[/bold yellow] {cmd}")
            if is_fast or click.confirm(f"Execute shell command: {cmd}?"):
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                feedback.append(f"Command Output: {res.stdout or res.stderr}")

        return "\n".join(feedback)

class AutonomousAgent(CopilotEngine):
    async def run_objective(self, objective: str):
        self.console.print(Panel(f"Mission: [bold green]{objective}[/bold green]", title="Autonomous Start"))
        loop_count, current_input = 0, objective
        while loop_count < 10:
            full_response = ""
            live = Live(Markdown(""), refresh_per_second=10, console=self.console)
            with self.console.status("[bold cyan]Agent is thinking... (Building Context)[/bold cyan]") as status:
                async for chunk in self.chat_stream(current_input):
                    if full_response == "":
                        status.stop()
                        live.start()
                    full_response += chunk
                    # Filter out messy <thought> tags and UI tags from the rendering only
                    clean_display = re.sub(r"<thought>.*?(?:</thought>|$)", "", full_response, flags=re.DOTALL)
                    clean_display = re.sub(r"\[(?:WRITE|COMMAND|SCAFFOLD):.*?\]", "", clean_display)
                    live.update(Markdown(clean_display.strip()))
            if live.is_started:
                live.stop()
                
            if "MISSION_COMPLETE" in full_response: break
            current_input = "Feedback: Actions completed. Continue task."
            loop_count += 1
