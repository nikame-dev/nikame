# Alembic Async Scaffold

A production-ready `alembic` migration environment wired up intrinsically for Asyncio SQLAlchemy (`asyncpg`).

## Usage

This module provides the `alembic/env.py` and template engine. You must still run `alembic init -t async alembic` in the root of your project to generate the base structure, but you copy these scaffolded files in to automatically wire it tightly into your FastCHEAT architecture.

1. Ensure `app.database.session.DATABASE_URL` is configured correctly.
2. Inside `alembic/env.py`, specifically uncomment the import section and import your application's Declarative Base, mapping it to `target_metadata`.

```python
from my_app.database.repository import Base
target_metadata = Base.metadata
```

Then simply autogenerate migrations:

```bash
alembic revision --autogenerate -m "Init db"
alembic upgrade head
```

## Gotchas

* FastCHEAT runs completely async, meaning if you try to use standard alembic workflows it will crash complaining about `greenlet` contexts. This specific `env.py` uses `asyncio.run()` wrappers and `async_engine_from_config` to parse everything seamlessly.
