import pytest
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Normally these would be imported from your project
# from app.main import app
# from app.dependencies.database import get_db

class DummySession:
    async def execute(self, query):
        pass

async def dummy_get_db() -> AsyncGenerator[DummySession, None]:
    yield DummySession()

async def mock_get_db() -> AsyncGenerator[DummySession, None]:
    # Custom mock session for testing
    yield DummySession()

@pytest.fixture
def test_app() -> FastAPI:
    """
    Creates a FastAPI app instance with dependency overrides applied.
    """
    # Import your app object here
    app = FastAPI()
    
    # Apply global overrides for testing
    # app.dependency_overrides[get_db] = mock_get_db
    
    yield app
    
    # Clear overrides after the test running
    app.dependency_overrides.clear()

@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """
    Returns a standard test client tied to the app with overrides.
    """
    return TestClient(test_app)

@pytest.fixture
def override_dependency(test_app: FastAPI):
    """
    A context manager-like pattern for highly specific, test-scoped overrides.
    Usage:
        def test_special_case(override_dependency):
            override_dependency(get_current_user, mock_admin_user)
            # execute test logic
    """
    overrides = []
    
    def _override(target_dep, new_dep):
        test_app.dependency_overrides[target_dep] = new_dep
        overrides.append(target_dep)
        
    yield _override
    
    for dep in overrides:
        test_app.dependency_overrides.pop(dep, None)
