import pytest
from pydantic import ValidationError

from nikame.core.config.schema import NikameConfig


def test_config_valid_modules() -> None:
    config = NikameConfig(
        name="test-project",
        modules=["database.postgres", "api.fastapi"]
    )
    assert len(config.modules) == 2
    assert "api.fastapi" in config.modules

def test_config_invalid_modules() -> None:
    with pytest.raises(ValidationError):
        NikameConfig(
            name="test-project",
            modules=["postgres"] # Not dotted
        )

def test_default_values() -> None:
    config = NikameConfig(name="test")
    assert config.version == "2.0"
    assert config.environment.target == "local"
