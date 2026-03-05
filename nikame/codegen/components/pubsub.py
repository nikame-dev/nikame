# NIKAME GENERATED — DO NOT EDIT DIRECTLY
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from nikame.codegen.base import BaseCodegen, CodegenContext, WiringInfo
from nikame.config.schema import NikameConfig


class PubSubCodegen(BaseCodegen):
    NAME = "pubsub"
    DESCRIPTION = "Redis-based Pub/Sub for event-driven communication"

    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx, config)
        self.config = config
        template_dir = Path(__file__).parent.parent.parent / "templates" / "codegen" / "components" / "pubsub"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(self) -> list[tuple[str, str]]:
        files = [
            ("app/events/pubsub.py", self.env.get_template("manager.py.j2").render()),
        ]
        return files

    def wiring(self) -> WiringInfo:
        return WiringInfo(
            requirements=["redis>=5.0.0"]
        )
