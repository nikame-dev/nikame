"""NIKAME CLI entry point.

Registers all Click commands under the `nikame` group.
All output uses rich.console — never print().
"""

from __future__ import annotations

import click

from nikame import __version__
from nikame.cli.commands.add import add
from nikame.cli.commands.db import db_group
from nikame.cli.commands.destroy import destroy
from nikame.cli.commands.diff import diff
from nikame.cli.commands.down import down
from nikame.cli.commands.github import github
from nikame.cli.commands.init import init
from nikame.cli.commands.login import login, logout, whoami
from nikame.cli.commands.logs import logs
from nikame.cli.commands.ml import ml_group
from nikame.cli.commands.regenerate import regenerate
from nikame.cli.commands.status import status
from nikame.cli.commands.up import up
from nikame.cli.commands.verify import verify
from nikame.cli.commands.preflight import preflight
from nikame.cli.commands.tunnel import tunnel
from nikame.cli.commands.templates import templates_group
from nikame.utils.logger import console, setup_logging


@click.group()
@click.version_option(version=__version__, prog_name="nikame")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """NIKAME — Describe your infrastructure. NIKAME builds it.

    An open-source infrastructure automation framework. One config
    file generates Docker Compose, K8s manifests, Terraform,
    CI/CD pipelines, ML serving, and observability — all
    compute-optimized by default.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    setup_logging(verbose=verbose)

    if verbose:
        console.print("[info]Debug logging enabled[/info]")


# Register commands
cli.add_command(init)
cli.add_command(up)
cli.add_command(down)
cli.add_command(destroy)
cli.add_command(add)
cli.add_command(db_group)
cli.add_command(diff)
cli.add_command(login)
cli.add_command(logout)
cli.add_command(logs)
cli.add_command(whoami)
cli.add_command(github)
cli.add_command(ml_group)
cli.add_command(regenerate)
cli.add_command(status)
cli.add_command(tunnel)
cli.add_command(verify)
cli.add_command(preflight)
cli.add_command(templates_group)


if __name__ == "__main__":
    cli()
