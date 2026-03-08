"""Schema-Driven Codegen Engine for NIKAME.

Iterates over declarative models in nikame.yaml and generates 
the full Async SQLAlchemy/Pydantic/FastAPI stack using Jinja2 templates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from nikame.config.schema import DataModelConfig, FieldConfig, NikameConfig
from nikame.utils.file_writer import FileWriter


from nikame.codegen.base import BaseCodegen, CodegenContext

class SchemaCodegen(BaseCodegen):
    """Engine to generate code from DataModelConfig."""
    NAME = "schema"
    DESCRIPTION = "SQLAlchemy/Pydantic stack generation from data models"

    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx, config)
        template_dir = Path(__file__).parent.parent / "templates" / "codegen" / "schema"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    @classmethod
    def should_trigger(cls, active_modules: set[str], active_features: set[str]) -> bool:
        """Trigger if either postgres or neo4j or clickhouse is present AND models are defined.
        Since we don't have the config here, we trigger if a DB is present.
        """
        db_modules = {"postgres", "neo4j", "clickhouse", "qdrant"}
        return any(m in active_modules for m in db_modules)

    def generate(self) -> list[tuple[str, str]]:
        """Render all model-based files."""
        if not self.config.models:
            return []
            
        files = []

        for name, model_cfg in self.config.models.items():
            context = self._build_context(name, model_cfg)

            # 1. Models
            model_content = self.env.get_template("model.py.j2").render(context)
            files.append((f"app/models/{name.lower()}.py", model_content))

            # 2. Schemas
            schema_content = self.env.get_template("schema.py.j2").render(context)
            files.append((f"app/schemas/{name.lower()}.py", schema_content))

            # 3. Routers
            router_content = self.env.get_template("router.py.j2").render(context)
            files.append((f"app/api/v1/endpoints/{name.lower()}.py", router_content))

        # 4. Seed Data Script
        seed_content = self.env.get_template("seed.py.j2").render({"models": list(self.config.models.keys())})
        files.append(("scripts/seed_db.py", seed_content))
        
        return files

        # 5. Migration (Simple skeleton)
        # In production, we assume the user runs 'alembic revision --autogenerate'
        # but we can provide a starting point.

    def _build_context(self, name: str, cfg: DataModelConfig) -> dict[str, Any]:
        """Prepare variables for Jinja."""
        fields = {}
        primary_key = "id"
        all_model_names = list(self.config.models.keys())

        # Ensure 'id' exists if not provided
        if "id" not in cfg.fields:
            fields["id"] = self._parse_field("int", primary_key=True)

        processed_relationships = {}

        # 1. Parse fields and detect relationships
        for f_name, f_val in cfg.fields.items():
            parsed_f = self._parse_field(f_val, all_model_names=all_model_names)

            if parsed_f["is_relationship"]:
                target_model = parsed_f["target_model"]
                rel_type = parsed_f["rel_type"]
                processed_relationships[f_name] = {
                    "type": rel_type,
                    "target_model": target_model,
                    "target_table": target_model.lower(),
                    "backref": f"{name.lower()}{'s' if rel_type == 'many-to-one' else ''}",
                    "id_type": "int",
                }
            else:
                fields[f_name] = parsed_f
                if parsed_f.get("primary_key"):
                    primary_key = f_name

        # 2. Add explicit relationships from config
        for r_name, r_cfg in cfg.relationships.items():
            processed_relationships[r_name] = {
                "type": r_cfg.type,
                "target_model": r_cfg.model,
                "target_table": r_cfg.model.lower(),
                "backref": r_cfg.backref or f"{name.lower()}{'s' if r_cfg.type == 'many-to-one' else ''}",
                "id_type": "int",
            }

        return {
            "model_name": name,
            "table_name": name.lower(),
            "primary_key": primary_key,
            "fields": fields,
            "relationships": processed_relationships,
            "soft_delete": cfg.soft_delete,
        }

    def _parse_field(self, field_val: FieldConfig | str, primary_key: bool = False, all_model_names: list[str] = []) -> dict[str, Any]:
        """Parse a field definition into template-ready context."""
        if isinstance(field_val, str):
            f_type_raw = field_val
            f_cfg = FieldConfig(type=field_val)
        else:
            f_type_raw = field_val.type
            f_cfg = field_val

        res = f_cfg.model_dump()
        res["is_relationship"] = False

        # Handle Relationship shorthand: category: Category
        if f_type_raw in all_model_names:
            res["is_relationship"] = True
            res["target_model"] = f_type_raw
            res["rel_type"] = "many-to-one"

        # Handle List Relationship: items: list[Product]
        elif f_type_raw.startswith("list[") and f_type_raw[5:-1] in all_model_names:
            res["is_relationship"] = True
            res["target_model"] = f_type_raw[5:-1]
            res["rel_type"] = "one-to-many"

        # Handle Enum: type="enum" with values=[...] OR shorthand: enum[val1, val2]
        elif f_type_raw == "enum" and f_cfg.values:
            res["enum_values"] = f_cfg.values
            res["python_type"] = "str"
            res["sa_type"] = "String"
        elif f_type_raw.startswith("enum["):
            vals = [v.strip() for v in f_type_raw[5:-1].split(",")]
            res["enum_values"] = vals
            res["python_type"] = "str"
            res["sa_type"] = "String"

        # Handle List Simple: images: list[str]
        elif f_type_raw.startswith("list["):
            inner_type = f_type_raw[5:-1]
            inner_ctx = self.TYPE_MAP.get(inner_type, {"py": "str", "sa": "String"})
            res["python_type"] = f"List[{inner_ctx['py']}]"
            res["sa_type"] = "JSON"

        # Handle Standard Types
        else:
            ctx = self.TYPE_MAP.get(f_type_raw, {"py": "str", "sa": "String"})
            res["python_type"] = ctx["py"]
            res["sa_type"] = ctx["sa"]

        res["default_repr"] = self._get_default_repr(res["default"])
        return res

    def _get_default_repr(self, val: Any) -> str:
        if val is None: return "None"
        if isinstance(val, str): return f"'{val}'"
        return str(val)
