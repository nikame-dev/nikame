import typer
from .commands import init, add, doctor, info, verify, agent

cli = typer.Typer(
    name="nikame",
    help="NIKAME: The Autonomous Systems Orchestrator",
    no_args_is_help=True
)

cli.add_typer(init.app, name="init")
cli.add_typer(add.app, name="add")
cli.add_typer(doctor.app, name="doctor")
cli.add_typer(info.app, name="info")
cli.add_typer(verify.app, name="verify")
cli.add_typer(agent.app, name="agent")

if __name__ == "__main__":
    cli()
