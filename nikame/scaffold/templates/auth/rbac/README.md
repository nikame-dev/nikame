# Role-Based Access Control (RBAC)

Provides role hierarchy and permission-based dependency factories to secure specific standard routes.

## Usage

Use `require_role(str)` to enforce a role hierarchy. 

```python
from fastapi import APIRouter, Depends
from app.auth.rbac import require_role

router = APIRouter()

# Requires manager role or anything higher in the hierarchy (e.g. admin)
@router.post("/delete")
async def delete_item(user = Depends(require_role("manager"))):
    return {"message": "Success"}
```

Use `require_permissions(List[str])` to require granular permissions.

```python
from app.auth.rbac import require_permissions

@router.get("/sensitive-data")
async def sensitive_data(user = Depends(require_permissions(["read:sensitive_data"]))):
    return {"data": "Secret"}
```

## Gotchas

* You MUST replace `_get_user_model` with actual fetching logic from your DB that maps a token identifier to a database User model.
* The explicit permission logic only has a stub (`user_permissions = ["read:data"]`). You will need to implement a true lookup or RBAC cross-reference table.
