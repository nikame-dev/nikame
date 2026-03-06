import os
from nikame.blueprint.engine import build_blueprint
from nikame.config.schema import NikameConfig
from nikame.codegen.features.auth import AuthCodegen
from nikame.codegen.features.search import SearchCodegen
from nikame.codegen.features.file_upload import FileUploadCodegen
from nikame.codegen.features.webhooks import WebhookCodegen
from nikame.codegen.features.rate_limiting import RateLimitingCodegen
from nikame.codegen.features.audit_log import AuditLogCodegen
from nikame.codegen.features.background_jobs import JobsCodegen
from nikame.modules.api.fastapi import FastApiModule

def test_codegen_with_features():
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
    class Ctx:
        def __init__(self, blueprint, features, config):
            self.blueprint = blueprint
            self.features = features
            self.project_name = config.name
            self.all_env_vars = {}
            
    ctx = Ctx(blueprint, config.features, config)
    
    print("--- Verifying FastAPI App core imports ---")
    fastapi_mod = FastApiModule(config.modules[4])
    fastapi_mod.ctx = ctx
    fastapi_files = fastapi_mod.scaffold_files()
    fastapi_main = next(content for path, content in fastapi_files if "fastapi.py" in path or "main.py" in path or "config.py" in path or "core/database.py" in path)
    
    # We just want to make sure it generated without errors
    print(f"FastAPI scaffold generated {len(fastapi_files)} files. Core Database length: {len([f for f in fastapi_files if 'database.py' in f[0]])}")

    print("--- Verifying Codegens ---")
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
        print(f"Generated {gen.NAME}: {len(files)} files. Connected to Kafka: {has_kafka}")

if __name__ == "__main__":
    test_codegen_with_features()
    print("Verification completed successfully!")
