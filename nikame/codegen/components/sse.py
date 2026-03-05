# NIKAME GENERATED — DO NOT EDIT DIRECTLY
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from nikame.codegen.base import BaseCodegen, CodegenContext, WiringInfo
from nikame.config.schema import NikameConfig


class SSECodegen(BaseCodegen):
    NAME = "sse"
    DESCRIPTION = "Server-Sent Events (SSE) for real-time updates"

    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx, config)
        self.config = config
        template_dir = Path(__file__).parent.parent.parent / "templates" / "codegen" / "components" / "sse"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(self) -> list[tuple[str, str]]:
        files = [
            ("app/sse/manager.py", self.env.get_template("manager.py.j2").render()),
            ("app/api/v1/endpoints/sse.py", self.env.get_template("router.py.j2").render()),
        ]
        return files

    def wiring(self) -> WiringInfo:
        return WiringInfo(
            imports=["from app.api.v1.endpoints.sse import router as sse_router"],
            routers=["app.include_router(sse_router)"],
            requirements=["sse-starlette>=1.8.2"]
        )
