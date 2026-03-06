import os
from typing import Any
from nikame.blueprint.engine import build_blueprint, Blueprint
from nikame.config.schema import NikameConfig
from nikame.codegen.features.auth import AuthCodegen
from nikame.codegen.features.search import SearchCodegen
from nikame.codegen.features.file_upload import FileUploadCodegen
from nikame.codegen.features.webhooks import WebhookCodegen
from nikame.codegen.features.rate_limiting import RateLimitingCodegen
from nikame.codegen.features.audit_log import AuditLogCodegen
from nikame.codegen.features.background_jobs import JobsCodegen
from nikame.modules.api.fastapi import FastApiModule
from nikame.utils.logger import console

def test_codegen_with_features() -> None:
    """Test codegen features with a full stack configuration."""
    config_dict = {
        "name": "test-project",
        "environment": {"target": "local"},
        "features": ["auth", "search", "file_upload", "background_jobs", "audit_log", "rate_limiting", "webhooks"],
        "modules": [
            {"name": "postgres"},
            {"name": "redpanda"},
            {"name": "dragonfly"},
            {"name": "minio"},
            {"name": "fastapi"},
            {"name": "ngrok"}
        ]
    }
    
    config = NikameConfig(**config_dict)
    blueprint = build_blueprint(config)
    
    # Context Mock
    class MockCtx:
        """Mock context for testing."""
        def __init__(self, blueprint: Blueprint, features: list[str], config: NikameConfig) -> None:
            self.blueprint = blueprint
            self.features = features
            self.project_name = config.name
            self.all_env_vars: dict[str, str] = {}
            self.active_modules: list[str] = [m.NAME for m in blueprint.modules]
            
    ctx: Any = MockCtx(blueprint, config.features, config)
    
    console.print("--- Verifying FastAPI App core imports ---")
    fastapi_mod = FastApiModule(config.modules[4], ctx)
    fastapi_files = fastapi_mod.scaffold_files()
    
    # We just want to make sure it generated without errors
    console.print(f"FastAPI scaffold generated {len(fastapi_files)} files. Core Database length: {len([f for f in fastapi_files if 'database.py' in f[0]])}")

    console.print("--- Verifying Codegens ---")
    codegens = [
        AuthCodegen(ctx),
        SearchCodegen(ctx),
        FileUploadCodegen(ctx),
        WebhookCodegen(ctx),
        RateLimitingCodegen(ctx),
        AuditLogCodegen(ctx),
        JobsCodegen(ctx)
    ]
    
    for gen in codegens:
        files = gen.generate()
        has_kafka = any("kafka_service" in content or "kafka" in content for path, content in files)
        console.print(f"Generated {gen.NAME}: {len(files)} files. Connected to Kafka: {has_kafka}")

if __name__ == "__main__":
    test_codegen_with_features()
    console.print("[success]Verification completed successfully![/success]")
