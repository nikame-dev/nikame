"""Payments feature codegen for NIKAME.

Provides Stripe integration for subscriptions.
"""

from __future__ import annotations

import os

from nikame.codegen.base import BaseCodegen
from nikame.codegen.registry import register_codegen


@register_codegen
class PaymentsCodegen(BaseCodegen):
    """Generates payment integration code."""

    NAME = "payments"
    DESCRIPTION = "Stripe checkout and webhooks"
    DEPENDENCIES: list[str] = ["auth"]
    MODULE_DEPENDENCIES: list[str] = []

    def generate(self) -> list[tuple[str, str]]:
        files = []
        template_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "templates", "features", "payments"
        )

        for template_name in ["service.py.j2", "router.py.j2"]:
            path = os.path.join(template_dir, template_name)
            with open(path) as f:
                content = f.read()

            target_path = f"services/api/payments/{template_name.replace('.j2', '')}"
            files.append((target_path, content))

        return files
