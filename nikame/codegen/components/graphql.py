# NIKAME GENERATED — DO NOT EDIT DIRECTLY
from pathlib import Path
from typing import Any, Dict
from jinja2 import Environment, FileSystemLoader

from nikame.codegen.base import BaseCodegen, CodegenContext, WiringInfo
from nikame.config.schema import NikameConfig

class GraphQLCodegen(BaseCodegen):
    NAME = "graphql"
    DESCRIPTION = "GraphQL API (Strawberry) auto-generated from schema"
    
    STRAWBERRY_TYPE_MAP = {
        "str": "str",
        "int": "int",
        "float": "float",
        "bool": "bool",
        "datetime": "datetime",
        "uuid": "uuid.UUID",
        "email": "str",
        "text": "str",
        "json": "str", # Strawberry JSON scalars need custom handling normally
    }

    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx)
        self.config = config
        template_dir = Path(__file__).parent.parent.parent / "templates" / "codegen" / "components" / "graphql"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(self) -> list[tuple[str, str]]:
        if not self.config.models:
            return []

        models_ctx = {}
        for name, model in self.config.models.items():
            fields = {}
            # Simplified field extraction for Strawberry
            # In a real impl, we'd use the same logic as SchemaCodegen
            from nikame.codegen.schema_codegen import SchemaCodegen
            temp_codegen = SchemaCodegen(self.config)
            context = temp_codegen._build_context(name, model)
            
            processed_fields = {}
            for f_name, f_ctx in context["fields"].items():
                py_type = f_ctx["python_type"]
                # Convert py types to strawberry-compatible strings if needed
                strawberry_type = py_type.replace("List", "List") # strawberry.type handles this
                processed_fields[f_name] = {"strawberry_type": strawberry_type}
            
            models_ctx[name] = {"fields": processed_fields}

        ctx = {"models": models_ctx}

        files = [
            ("app/graphql/types.py", self.env.get_template("types.py.j2").render(ctx)),
            ("app/graphql/schema.py", self.env.get_template("schema.py.j2").render(ctx)),
            ("app/api/v1/endpoints/graphql.py", self.env.get_template("router.py.j2").render(ctx)),
        ]
        return files

    def wiring(self) -> WiringInfo:
        return WiringInfo(
            imports=["from app.api.v1.endpoints.graphql import router as graphql_router"],
            routers=["app.include_router(graphql_router, prefix=\"/graphql\")"],
            requirements=["strawberry-graphql[fastapi]>=0.219.0"]
        )
