"""Terraform composer for NIKAME."""
from __future__ import annotations

from nikame.blueprint.engine import Blueprint
from nikame.composers.terraform.aws import AWSTerraformProvider


def generate_terraform(blueprint: Blueprint) -> dict[str, str]:
    """Generate Terraform files based on the blueprint cloud target."""
    cloud = blueprint.modules[0].ctx.cloud if blueprint.modules else "aws"

    # Default to AWS for now as it's the required implementation
    provider = AWSTerraformProvider()
    return provider.generate(blueprint)
