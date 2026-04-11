import asyncio
import json
import httpx
import re
import subprocess
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
    """Core engine for the NIKAME Copilot chat session."""
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
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                async with client.stream(
                    "POST", 
                    f"{self.client.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": self.history,
                        "stream": True,
                        "options": {
                            "num_ctx": 16384 if self.mode == "planning" else 8192,
                            "temperature": 0.2
                        }
                    }
                ) as response:
                    full_response = ""
                    async for line in response.aiter_lines():
                        if not line: continue
                        data = json.loads(line)
                        if "message" in data:
                            content = data["message"].get("content", "")
                            full_response += content
                            yield content
                        if data.get("done"):
                            self.history.append({"role": "assistant", "content": full_response})
                            await self._process_tool_calls(full_response)
            except Exception as e:
                yield f"\n[red]Error: {str(e)}[/red]"

    async def _process_tool_calls(self, text: str):
        """Parse and execute bracketed commands."""
        # 1. SCAFFOLD
        scaffold_matches = re.findall(r"\[SCAFFOLD:\s*([^\]]+)\]", text)
        for slug in scaffold_matches:
             slug = slug.strip()
             self.console.print(f"[cyan]✨ Action: Scaffolding {slug}[/cyan]")
             if click.confirm(f"Execute 'nikame scaffold add {slug}'?"):
                 get_scaffolder().scaffold(slug, Path("."))
                 state = self.context.state.load()
                 patterns = state.get("installed_patterns", [])
                 if slug not in patterns: patterns.append(slug)
                 self.context.state.update(installed_patterns=patterns, last_action=f"scaffold {slug}")

        # 2. WRITE
        write_pattern = r"\[WRITE:\s*([^\]]+)\]\s*```[a-z]*\n(.*?)\n```"
        for match in re.finditer(write_pattern, text, re.DOTALL):
            target = Path(match.group(1).strip())
            content = match.group(2)
            self.console.print(Panel(f"Action: Writing to {target}", border_style="yellow"))
            if click.confirm(f"Commit changes to {target}?"):
                self.file_manager.create_backup(target)
                target.write_text(content)
                self.context.state.update(last_action=f"write {target}")

class AutonomousAgent(CopilotEngine):
    """Closed-loop Autonomous Agent for NIKAME."""
    def __init__(self, model_name: str, mode: str = "planning"):
        super().__init__(model_name, mode)
        self.max_loops = 5

    async def initialize(self):
        await super().initialize()
        self.history[0]["content"] += """
        
AUTONOMOUS AGENT MODE:
- You must always output your reasoning in a <thought> block.
- You have the power to SELF-HEAL. If a command fails, analyze the output and try again.
- When finished, generate a REPORT.md in the project root.
- Tools: [SCAFFOLD: slug], [WRITE: path], [COMMAND: cmd], [VERIFY: smoke].
- If you have reached the objective, output: MISSION_COMPLETE.
"""

    async def run_objective(self, objective: str):
        self.console.print(Panel(f"Target Objective: [bold green]{objective}[/bold green]", title="Autonomous Mission Start"))
        loop_count = 0
        current_input = objective
        
        while loop_count < self.max_loops:
            full_response = ""
            with Live(Markdown(""), refresh_per_second=10, console=self.console) as live:
                async for chunk in self.chat_stream(current_input):
                    full_response += chunk
                    live.update(Markdown(full_response))
            
            if "MISSION_COMPLETE" in full_response:
                self.console.print("[success]✓ Objective Reached.[/success]")
                break
            
            current_input = "Analyze current state and continue towards objective. If done, say MISSION_COMPLETE."
            loop_count += 1
