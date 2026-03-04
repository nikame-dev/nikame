# NIKAME GENERATED — DO NOT EDIT DIRECTLY
from pathlib import Path
from nikame.codegen.base import BaseCodegen, CodegenContext, WiringInfo
from nikame.config.schema import NikameConfig
from jinja2 import Environment, FileSystemLoader

class VectorSearchCodegen(BaseCodegen):
    NAME = "vector_search"
    DESCRIPTION = "Semantic vector search (Qdrant + sentence-transformers)"

    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx)
        self.config = config
        template_dir = Path(__file__).parent.parent.parent / "templates" / "codegen" / "components" / "vector_search"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(self) -> list[tuple[str, str]]:
        files = [
            ("app/search/vector.py", self.env.get_template("vector.py.j2").render()),
        ]
        return files

    def wiring(self) -> WiringInfo:
        return WiringInfo(
            requirements=["qdrant-client>=1.8.0", "sentence-transformers>=2.5.0"]
        )
