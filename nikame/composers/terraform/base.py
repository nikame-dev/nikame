"""Terraform base composer for NIKAME."""
from __future__ import annotations

from abc import ABC, abstractmethod

from nikame.blueprint.engine import Blueprint


class BaseTerraformProvider(ABC):
    """Abstract base class for all Terraform cloud providers."""

    @abstractmethod
    def generate(self, blueprint: Blueprint) -> dict[str, str]:
        """Generate Terraform files (.tf)."""
        pass
