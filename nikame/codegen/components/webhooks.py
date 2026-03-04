# NIKAME GENERATED — DO NOT EDIT DIRECTLY
from pathlib import Path
from nikame.codegen.base import BaseCodegen, CodegenContext, WiringInfo
from nikame.config.schema import NikameConfig
from jinja2 import Environment, FileSystemLoader

class WebhookCodegen(BaseCodegen):
    NAME = "webhooks"
    DESCRIPTION = "Webhook receiver with signature verification"

    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx)
        self.config = config
        template_dir = Path(__file__).parent.parent.parent / "templates" / "codegen" / "components" / "webhooks"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(self) -> list[tuple[str, str]]:
        files = [
            ("app/webhooks/security.py", self.env.get_template("security.py.j2").render()),
            ("app/api/v1/endpoints/webhooks.py", self.env.get_template("router.py.j2").render()),
        ]
        return files

    def wiring(self) -> WiringInfo:
        return WiringInfo(
            imports=["from app.api.v1.endpoints.webhooks import router as webhooks_router"],
            routers=["app.include_router(webhooks_router)"]
        )
