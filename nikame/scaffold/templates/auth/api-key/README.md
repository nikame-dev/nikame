# API Key Authentication

Provides simple but robust API Key authentication by allowing keys to be submitted via the `X-API-Key` HTTP Header or the `?api_key=` URL query parameter.

## Usage

You can use the dependency `require_api_key` in any of your routes to enforce that the route requires a valid API key.

```python
from fastapi import APIRouter, Depends, Security
from app.auth.api_key import require_api_key

router = APIRouter()

@router.get("/data")
async def get_secure_data(user: str = Security(require_api_key)):
    return {"message": "Authenticated successfully!", "user": user}
```

## Gotchas

* Never hardcode API keys. In the stub we provide a dummy dictionary, but this should be swapped out for a secure DB lookup that checks encrypted hashes of API keys out of a backend store.
* Prefer Header-based authentication over Query string for security and caching reasons (proxy logs often write down query parameters, exposing keys).
