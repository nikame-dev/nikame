# NIKAME GENERATED — DO NOT EDIT DIRECTLY
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from nikame.codegen.base import BaseCodegen, CodegenContext, WiringInfo
from nikame.config.schema import NikameConfig


class MockDataCodegen(BaseCodegen):
    NAME = "mock_data"
    DESCRIPTION = "Random data / mock API generator (Faker-based)"

    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx, config)
        self.config = config
        template_dir = Path(__file__).parent.parent.parent / "templates" / "codegen" / "components" / "mock_data"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(self) -> list[tuple[str, str]]:
        if not self.config.models:
            return []

        # Simplified context for the generator
        models_ctx = {}
        for name, model in self.config.models.items():
            from nikame.codegen.schema_codegen import SchemaCodegen
            temp_codegen = SchemaCodegen(self.config)
            context = temp_codegen._build_context(name, model)
            models_ctx[name] = {"fields": context["fields"]}

        ctx = {"models": models_ctx}

        files = [
            ("scripts/seed_mock.py", self.env.get_template("seed_mock.py.j2").render(ctx)),
            ("app/api/v1/endpoints/mock_data.py", self.env.get_template("router.py.j2").render(ctx)),
        ]
        return files

    def wiring(self) -> WiringInfo:
        return WiringInfo(
            imports=["from app.api.v1.endpoints.mock_data import router as mock_router"],
            routers=["app.include_router(mock_router)"],
            requirements=["Faker>=23.0.0"]
        )
