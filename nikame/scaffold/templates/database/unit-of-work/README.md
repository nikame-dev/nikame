# Unit of Work

The Unit of Work pattern abstract database transactions and repository lifecycles into a single boundary. This allows you to perform multiple operations across multiple repositories and commit them all atomically or roll them all back if an exception occurs.

## Usage

Create your UoW class that registers your repositories so they all share the exact same `session`:

```python
from app.database.uow import AbstractUnitOfWork, UnitOfWork

# Inside your service layer
async def create_user_with_profile(uow: AbstractUnitOfWork, user_data, profile_data):
    # This block represents the transaction boundary
    async with uow:
        # Both operations share one session
        user = await uow.users.create(user_data)
        profile_data["user_id"] = user.id
        await uow.profiles.create(profile_data)
        # If no exceptions are raised, `__aexit__` automatically calls commit
```

Inject via FastAPI routes:

```python
from fastapi import APIRouter, Depends
from app.database.uow import UnitOfWork, get_uow

router = APIRouter()

@router.post("/register")
async def register(uow: UnitOfWork = Depends(get_uow)):
    async with uow:
       await uow.users.get(...)
```

## Gotchas

* Any unhandled exceptions bubbling up through the `async with uow:` block will automatically trigger `uow.rollback()`.
* You should define attributes like `self.users = UserRepository(session)` inside the `UnitOfWork.__init__` body to use this correctly.
