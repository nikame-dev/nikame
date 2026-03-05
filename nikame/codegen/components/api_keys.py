# NIKAME GENERATED — DO NOT EDIT DIRECTLY
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from nikame.codegen.base import BaseCodegen, CodegenContext, WiringInfo
from nikame.config.schema import NikameConfig


class APIKeyCodegen(BaseCodegen):
    NAME = "api_keys"
    DESCRIPTION = "Public API key system (generate, revoke, rate limit per key)"

    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx, config)
        template_dir = (
            Path(__file__).parent.parent.parent
            / "templates"
            / "codegen"
            / "components"
            / "api_keys"
        )
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(self) -> list[tuple[str, str]]:
        files = [
            (
                "app/auth/api_keys.py",
                self.env.get_template("auth.py.j2").render(),
            ),
            (
                "app/api/v1/endpoints/api_keys.py",
                self.env.get_template("router.py.j2").render(),
            ),
        ]
        return files

    def wiring(self) -> WiringInfo:
        return WiringInfo(
            imports=[
                "from app.api.v1.endpoints.api_keys import router as api_keys_router"
            ],
            routers=["app.include_router(api_keys_router)"],
        )
