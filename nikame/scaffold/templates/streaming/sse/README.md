# Server-Sent Events (SSE)

Provides a standard unidirectional streaming router utilizing `sse-starlette`. 

SSE is dramatically easier to implement client-side (standard browser `EventSource` object) than full WebSockets when you only need server-to-client push updates (like progress bars or live logs).

## Usage

Mount the router:

```python
from fastapi import FastAPI
from app.routers.sse import router as sse_router

app = FastAPI()
app.include_router(sse_router)
```

Test from a terminal:

```bash
curl -N http://localhost:8000/stream/events
```

## Gotchas

* If you are running Uvicorn behind Nginx/ALB/HAProxy, these proxies typically buffer responses or kill long-running idle connections. To fix this, you must build proper "Ping" messages and check `await request.is_disconnected()`. If you don't check for disconnects, you will leak memory indefinitely.
* Because this is raw HTTP streaming, Python connections pool up quickly. Make sure your worker class is truly async (UvicornWorker) and not blocking on threads.
