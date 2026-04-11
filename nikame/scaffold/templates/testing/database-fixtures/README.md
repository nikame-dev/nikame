# Database Test Fixtures

Advanced database testing for SQLAlchemy and FastAPI.

## The "Perfect" Test Strategy

This module implements the **Nested Transaction (Savepoint) Pattern**:
1.  **Session Start**: Create the database schema once.
2.  **Test Start**: Start a connection and a Top-Level transaction.
3.  **App Run**: Inject the session into FastAPI.
4.  **Test End**: Roll back the Top-Level transaction.

Result: Your database is always pristine for the next test, and no actual data is ever committed to disk, making tests incredibly fast.

## Usage

1. Configure `TEST_DATABASE_URL` (usually an in-memory SQLite for speed or a separate Postgres DB for compatibility).
2. Inherit/Import the fixtures in your tests.

```python
@pytest.mark.asyncio
async def test_create_user(client, db_session, override_get_db):
    # This test is atomic. Even if it crashes, the DB stays clean.
    resp = await client.post("/users", json={"name": "Alice"})
    assert resp.status_code == 201
```

## Gotchas

-   **SQLite Limitations**: If you use `sqlite:///:memory:`, keep in mind that SQLite doesn't support some advanced Postgres features like `JSONB` or `Array`. 
-   **Session Scope**: Ensure `test_engine` is session-scoped to avoid the heavy overhead of recreating tables for every single file.
