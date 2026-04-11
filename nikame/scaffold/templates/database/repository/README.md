# Generic Repository

An abstract class using Python's `Generic` and TypeVars to provide fully typed CRUD methods over your SQLAlchemy ORM models. This drastically cuts down on boilerplate since fetching, creating, computing counts, and executing soft-updates are implemented cleanly once.

## Usage

Extend the `BaseRepository` for each ORM model:

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pydantic import BaseModel
from fastcheat.database.repository import BaseRepository

class Base(DeclarativeBase):
    pass

# Your definitions
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]

class UserCreate(BaseModel):
    email: str

class UserUpdate(BaseModel):
    email: str | None = None

# Your specialized repository
class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    def __init__(self, session):
        super().__init__(User, session)
        
    async def get_by_email(self, email: str) -> User | None:
        """Add custom queries specifically for Users here"""
        from sqlalchemy import select
        res = await self.session.execute(select(User).where(User.email == email))
        return res.scalars().first()
```

## Gotchas

* `commits()` are not executed by the generic repository. This is intentional. You should group operations logically inside a router endpoint or Service layer and execute `await db.commit()` at the boundary or use the `unit-of-work` pattern.
* Expects `self.model.id` to exist as the primary key. If you use UUIDs or compound keys you'll need to override `get()`.
