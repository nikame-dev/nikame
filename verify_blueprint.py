from nikame.config.schema import NikameConfig
from nikame.blueprint.engine import build_blueprint
import pydantic

def test_feature_resolution():
    config_dict = {
        "name": "test-project",
        "environment": {"target": "local", "profile": "local"},
        "api": {"framework": "fastapi"},
        "features": ["auth", "file_upload", "search"]
    }
    
    config = NikameConfig(**config_dict)
    print(f"Testing resolution for features: {config.features}")
    
    blueprint = build_blueprint(config)
    
    active_modules = [m.NAME for m in blueprint.modules]
    print(f"Resolved modules: {active_modules}")
    
    # Check for dependencies
    # auth -> postgres
    # file_upload -> minio
    # search -> postgres
    
    required = ["postgres", "minio", "fastapi"]
    missing = [m for m in required if m not in active_modules]
    
    if not missing:
        print("✅ SUCCESS: All feature dependencies resolved and added to blueprint.")
    else:
        print(f"❌ FAILURE: Missing modules: {missing}")

if __name__ == "__main__":
    test_feature_resolution()
