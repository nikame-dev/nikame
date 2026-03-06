from __future__ import annotations

from nikame.blueprint.engine import build_blueprint
from nikame.config.schema import NikameConfig
from nikame.utils.logger import get_logger

_log = get_logger("verify_blueprint")


def test_feature_resolution() -> None:
    """Verify that feature-to-module dependencies are correctly resolved."""
    config_dict = {
        "name": "test-project",
        "environment": {"target": "local", "profile": "local"},
        "api": {"framework": "fastapi"},
        "features": ["auth", "file_upload", "search"],
    }

    config = NikameConfig(**config_dict)
    _log.info("Testing resolution for features: %s", config.features)

    blueprint = build_blueprint(config)

    active_modules = [m.NAME for m in blueprint.modules]
    _log.info("Resolved modules: %s", active_modules)

    # Check for dependencies
    required = ["postgres", "minio", "fastapi"]
    missing = [m for m in required if m not in active_modules]

    if not missing:
        _log.info("✅ SUCCESS: All feature dependencies resolved.")
    else:
        _log.error("❌ FAILURE: Missing modules: %s", missing)


if __name__ == "__main__":
    test_feature_resolution()
