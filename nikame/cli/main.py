import typer

from .commands import (
    add,
    agent,
    diff,
    doctor,
    info,
    infra,
    init,
    list_patterns,
    rollback,
    stub,
    verify,
)

cli = typer.Typer(
    name="nikame",
    help="NIKAME: The Autonomous Systems Orchestrator",
    no_args_is_help=True,
    rich_markup_mode="rich"
)

# Register commands directly from modules
# This allows for a cleaner CLI structure: nikame <command> <args>
cli.command(name="init", help="Initialize a new project")(init.main)
cli.command(name="add", help="Add a pattern to project")(add.main)
cli.command(name="agent", help="Start the autonomous agent (TUI)")(agent.main)

# Inspection & Registry commands
cli.command(name="list", help="List available patterns")(list_patterns.main)
cli.command(name="info", help="Show pattern details")(info.main)
cli.command(name="diff", help="Preview pattern changes")(diff.main)
cli.command(name="stub", help="Generate AST stubs")(stub.main)

# Health & Infrastructure commands
cli.command(name="verify", help="Verify project integrity")(verify.main)
cli.command(name="doctor", help="Check environment health")(doctor.main)
cli.command(name="rollback", help="Rollback to a snapshot")(rollback.main)
cli.add_typer(infra.app, name="infra")


if __name__ == "__main__":
    cli()
