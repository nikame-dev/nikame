# NIKAME GENERATED — DO NOT EDIT DIRECTLY
from pathlib import Path
from nikame.codegen.base import BaseCodegen, CodegenContext, WiringInfo
from nikame.config.schema import NikameConfig
from jinja2 import Environment, FileSystemLoader

class MultiTenancyCodegen(BaseCodegen):
    NAME = "multi_tenancy"
    DESCRIPTION = "Org-based data isolation (Multi-tenancy)"

    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx)
        self.config = config
        template_dir = Path(__file__).parent.parent.parent / "templates" / "codegen" / "components" / "multi_tenancy"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(self) -> list[tuple[str, str]]:
        files = [
            ("app/models/multi_tenancy.py", self.env.get_template("models.py.j2").render()),
            ("app/api/deps_tenant.py", self.env.get_template("deps.py.j2").render()),
        ]
        return files

    def wiring(self) -> WiringInfo:
        return WiringInfo(
            imports=["from app.api.deps_tenant import get_current_tenant"],
            requirements=["sqlalchemy>=2.0.0"]
        )
