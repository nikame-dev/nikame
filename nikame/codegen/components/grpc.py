# NIKAME GENERATED — DO NOT EDIT DIRECTLY
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from nikame.codegen.base import BaseCodegen, CodegenContext, WiringInfo
from nikame.config.schema import NikameConfig


class GRPCCodegen(BaseCodegen):
    NAME = "grpc"
    DESCRIPTION = "gRPC service with auto-generated protobuf definitions"

    PROTO_TYPES = {
        "str": "string",
        "int": "int32",
        "float": "float",
        "bool": "bool",
        "datetime": "string",
        "uuid": "string",
        "email": "string",
        "text": "string",
    }

    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx, config)
        self.config = config
        template_dir = Path(__file__).parent.parent.parent / "templates" / "codegen" / "components" / "grpc"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(self) -> list[tuple[str, str]]:
        if not self.config.models:
            return []

        files = []
        for name, model in self.config.models.items():
            from nikame.codegen.schema_codegen import SchemaCodegen
            temp_codegen = SchemaCodegen(self.config)
            context = temp_codegen._build_context(name, model)
            context["project_name"] = self.ctx.project_name
            context["proto_types"] = self.PROTO_TYPES

            files.append((f"protos/{name.lower()}.proto", self.env.get_template("service.proto.j2").render(context)))
            files.append((f"app/grpc/{name.lower()}_server.py", self.env.get_template("server.py.j2").render(context)))

        return files

    def wiring(self) -> WiringInfo:
        return WiringInfo(
            requirements=["grpcio>=1.60.0", "grpcio-tools>=1.60.0"]
        )
