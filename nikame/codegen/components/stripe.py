# NIKAME GENERATED — DO NOT EDIT DIRECTLY
from pathlib import Path
from nikame.codegen.base import BaseCodegen, CodegenContext, WiringInfo
from nikame.config.schema import NikameConfig
from jinja2 import Environment, FileSystemLoader

class StripeCodegen(BaseCodegen):
    NAME = "stripe"
    DESCRIPTION = "Stripe subscription billing and webhook integration"

    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx)
        self.config = config
        template_dir = Path(__file__).parent.parent.parent / "templates" / "codegen" / "components" / "stripe"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(self) -> list[tuple[str, str]]:
        files = [
            ("app/api/v1/endpoints/billing.py", self.env.get_template("router.py.j2").render()),
        ]
        return files

    def wiring(self) -> WiringInfo:
        return WiringInfo(
            imports=["from app.api.v1.endpoints.billing import router as billing_router"],
            routers=["app.include_router(billing_router)"],
            requirements=["stripe>=8.0.0"]
        )
