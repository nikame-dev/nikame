# NIKAME GENERATED — DO NOT EDIT DIRECTLY
from pathlib import Path
from nikame.codegen.base import BaseCodegen, CodegenContext, WiringInfo
from nikame.config.schema import NikameConfig
from jinja2 import Environment, FileSystemLoader

class RateLimitingCodegen(BaseCodegen):
    NAME = "rate_limiting"
    DESCRIPTION = "Redis-backed IP rate limiting"

    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx)
        self.config = config
        template_dir = Path(__file__).parent.parent.parent / "templates" / "codegen" / "components" / "rate_limiting"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(self) -> list[tuple[str, str]]:
        files = [
            ("app/middleware/rate_limit.py", self.env.get_template("limiter.py.j2").render()),
        ]
        return files

    def wiring(self) -> WiringInfo:
        return WiringInfo(
            requirements=["redis>=5.0.0"]
        )
