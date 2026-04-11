# Request ID Middleware

Generates an `X-Request-ID` UUID for every incoming request if one was not provided, and injects it into both the request state execution context and the final HTTP response headers.

## Usage

Mount it into your main factory or `main.py`:

```python
from fastapi import FastAPI
from app.middleware.request_id import RequestIDMiddleware, get_request_id

app = FastAPI()
app.add_middleware(RequestIDMiddleware)

@app.get("/track")
async def get_tracking_id():
    # Will print the correct request ID for this context
    return {"my_id": get_request_id()}
```

## Gotchas
* Ensure this is one of your outermost middlewares (added last in FastAPI, meaning it runs first) so that inner exception handlers or loggers have access to the ID.
