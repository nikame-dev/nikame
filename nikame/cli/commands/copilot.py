import asyncio
import click
import questionary
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

from nikame.copilot.core.ollama import OllamaClient
from nikame.copilot.core.engine import CopilotEngine, AutonomousAgent

console = Console()

async def get_model():
    client = OllamaClient()
    models = await client.list_models()
    if not models:
        console.print("[red]No models found in Ollama. Ensure Ollama is running ('ollama serve') and models are pulled ('ollama pull llama3').[/red]")
        return None
    
    choice = await questionary.select(
        "Select active LLM:",
        choices=models
    ).ask_async()
    return choice

async def select_model_and_mode():
    client = OllamaClient()
    models = await client.list_models()
    if not models:
        console.print("[red]No brands/models found in Ollama.[/red]")
        return None, None
    
    model = await questionary.select(
        "Select active LLM:",
        choices=models
    ).ask_async()

    mode = await questionary.select(
        "Select Operation Mode:",
        choices=[
            questionary.Choice("Fast (Quick actions, low context latency)", "fast"),
            questionary.Choice("Planning (Deep context, architectural reasoning)", "planning")
        ]
    ).ask_async()
    
    return model, mode

async def run_chat(model: str, mode: str):
    engine = CopilotEngine(model, mode)
    await engine.initialize()
    
    mode_style = "green" if mode == "fast" else "bold magenta"
    console.print(Panel(
        f"NIKAME Copilot: [bold cyan]{model}[/bold cyan]\nMode: [{mode_style}]{mode.upper()}[/{mode_style}]\nContext Engineering: ACTIVE", 
        title="Project Brain", 
        border_style="cyan"
    ))
    
    while True:
        user_input = await questionary.text(">>>", qmark="").ask_async()
        if not user_input or user_input.lower() in ['exit', 'quit']:
            break
            
        full_content = ""
        with console.status(f"[bold]LLM Thinking ({mode})...[/bold]"):
            pass

        with Live(Markdown(""), refresh_per_second=10, console=console) as live:
            async for chunk in engine.chat_stream(user_input):
                full_content += chunk
                live.update(Markdown(full_content))

@click.command(name="copilot")
@click.argument("query", required=False)
def copilot_cmd(query: str = None):
    """Local-first AI Context-aware Coding Assistant."""
    model, mode = asyncio.run(select_model_and_mode())
    if not model:
        return

    if query:
        engine = CopilotEngine(model, mode)
        asyncio.run(engine.initialize())
        asyncio.run(_do_one_shot(engine, query))
    else:
        asyncio.run(run_chat(model, mode))

async def _do_one_shot(engine, query):
    full_content = ""
    with Live(Markdown(""), refresh_per_second=10, console=console) as live:
        async for chunk in engine.chat_stream(query):
            full_content += chunk
            live.update(Markdown(full_content))

@click.command(name="agent")
@click.argument("objective", required=True)
@click.option("--model", default=None, help="Force specific model.")
def agent_cmd(objective: str, model: str):
    """Launch NIKAME Autonomous Agent to reach a specific objective."""
    if not model:
        model_choice = asyncio.run(get_model())
        if not model_choice: return
        model = model_choice

    agent = AutonomousAgent(model)
    asyncio.run(agent.initialize())
    asyncio.run(agent.run_objective(objective))
