# NIKAME GENERATED — DO NOT EDIT DIRECTLY
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from nikame.codegen.base import BaseCodegen, CodegenContext, WiringInfo
from nikame.config.schema import NikameConfig


class HealthCheckCodegen(BaseCodegen):
    NAME = "health_check"
    DESCRIPTION = "Standardized health check API for DB, Redis, and system status"

    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx, config)
        self.config = config
        template_dir = Path(__file__).parent.parent.parent / "templates" / "codegen" / "components" / "health_check"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(self) -> list[tuple[str, str]]:
        files = [
            ("app/api/v1/endpoints/health.py", self.env.get_template("router.py.j2").render()),
        ]
        return files

    def wiring(self) -> WiringInfo:
        return WiringInfo(
            imports=["from app.api.v1.endpoints.health import router as health_router"],
            routers=["app.include_router(health_router)"]
        )
