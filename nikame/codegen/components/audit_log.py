# NIKAME GENERATED — DO NOT EDIT DIRECTLY
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from nikame.codegen.base import BaseCodegen, CodegenContext, WiringInfo
from nikame.config.schema import NikameConfig


class AuditLogCodegen(BaseCodegen):
    NAME = "audit_log"
    DESCRIPTION = "Model change history tracking (Audit Log)"

    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx, config)
        self.config = config
        template_dir = Path(__file__).parent.parent.parent / "templates" / "codegen" / "components" / "audit_log"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(self) -> list[tuple[str, str]]:
        files = [
            ("app/models/audit_log.py", self.env.get_template("model.py.j2").render()),
        ]
        return files

    def wiring(self) -> WiringInfo:
        return WiringInfo(
            requirements=["sqlalchemy>=2.0.0"]
        )
