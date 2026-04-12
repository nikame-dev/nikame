import pytest
from pathlib import Path
from nikame.engines.scaffold import ScaffoldEngine
from nikame.core.registry.loader import RegistryLoader

@pytest.fixture
def registry_loader():
    return RegistryLoader(Path("registry"))

@pytest.fixture
def scaffolder():
    return ScaffoldEngine()

def test_render_auth_jwt(registry_loader, scaffolder, tmp_path):
    """Verifies that the auth.jwt pattern renders expected files."""
    pattern = registry_loader.load_pattern("auth.jwt")
    assert pattern is not None
    
    context = {
        "JWT_SECRET_KEY": "test-secret",
        "JWT_ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": 30
    }
    
    # We'll mock the write to check content instead of writing to disk for this test
    # or use tmp_path
    
    for inj in pattern.injects:
         if inj.operation == "create" and inj.template:
             template_path = Path("registry/patterns/auth/jwt/templates") / inj.template
             if not template_path.exists():
                 continue
                 
             content = scaffolder.render_template(template_path.read_text(), context)
             
             # Assert some generic properties of 'auth.jwt' output
             if "router.py" in inj.path:
                 assert "APIRouter" in content
                 assert "/auth" in content
             if "security.py" in inj.path:
                 assert "create_access_token" in content
                 assert "SECRET_KEY" in content

def test_render_database_postgres(registry_loader, scaffolder):
    """Verifies that the database.postgres pattern renders expected files."""
    pattern = registry_loader.load_pattern("database.postgres")
    assert pattern is not None
    
    context = {
        "POSTGRES_USER": "testuser",
        "POSTGRES_PASSWORD": "testpassword",
        "POSTGRES_DB": "testdb"
    }
    
    for inj in pattern.injects:
         if inj.operation == "create" and inj.template:
             template_path = Path("registry/patterns/database/postgres/templates") / inj.template
             if not template_path.exists():
                 continue
                 
             content = scaffolder.render_template(template_path.read_text(), context)
             
             if "database.py" in inj.path:
                 assert "create_engine" in content
                 assert "Session" in content
