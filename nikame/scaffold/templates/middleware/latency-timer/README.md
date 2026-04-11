# Latency Timer Middleware

Calculates precise wall-clock processing time for incoming HTTP requests and automatically appends it to out-going headers.

## Usage

Mount it into your main factory or `main.py`:

```python
from fastapi import FastAPI
from app.middleware.latency import LatencyTimerMiddleware

app = FastAPI()
app.add_middleware(LatencyTimerMiddleware)
```

Clients hitting your application will now receive an `X-Process-Time` HTTP header like `X-Process-Time: 0.1451` on all requests. 

If requests take longer than the module `SLOW_REQUEST_THRESHOLD_SEC` variable, the server will dump a `warning`-level log with exact path characteristics automatically.

## Gotchas
* Ensure this is one of your outermost middlewares so it captures the time taken by auth injection or DB lookups. If added too far down, your latency metric will artificially under-report the total edge latency.
