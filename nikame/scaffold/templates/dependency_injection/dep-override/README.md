# Dependency Override

This pattern provides a structured way to override FastAPI dependencies during tests (`app.dependency_overrides`).

It includes testing fixtures to automatically clear overrides after tests run, avoiding state leakage between units, and it provides a dynamic `override_dependency` fixture to use per-test.

## Usage

In your pytest test file:

```python
from fastapi import Depends
from app.dependencies import get_current_user
from tests.fixtures.override import override_dependency, TestClient

def mock_user():
    return {"id": "1", "role": "admin"}

def test_admin_access(client: TestClient, override_dependency):
    # Override only for this test
    override_dependency(get_current_user, mock_user)
    
    response = client.get("/admin")
    assert response.status_code == 200
```
