# Async Client Fixtures

Provides the essential boilerplate for testing FastAPI with **`pytest-asyncio`** and **`httpx.AsyncClient`**.

## Why Async Testing?

FastAPI is inherently asynchronous. Standard `TestClient` uses a synchronous wrapper that doesn't always behave correctly with `lifespan` events or background tasks. Using `AsyncClient` ensures your tests accurately reflect production behavior.

## Usage

1. Create a `tests/` directory.
2. The provided `conftest.py` will automatically provide a `client` fixture.

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_my_endpoint(client: AsyncClient):
    response = await client.get("/v1/data")
    assert response.status_code == 200
```

## Gotchas

-   **Event Loop Scope**: By default, `pytest-asyncio` creates a new event loop per test, which can cause issues with singleton database connections. We've included a session-scoped loop override in `conftest.py` to fix this.
-   **Transaction Cleaning**: These fixtures do *not* automatically clean the database. Use **Database Test Fixtures** for state-dependent tests.
