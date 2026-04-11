# Environment CORS Pipeline

An explicit `setup_cors()` setup routine to handle injecting CORS middleware safely.

Far too often developers leave `allow_origins=["*"]` on globally and ship it to production. This setup hook looks at the server environment and forces lockdown if you are not strictly in "dev". 

## Usage

Run `setup_cors` cleanly at the top inside `fastapi` application assembly:

```python
from fastapi import FastAPI
from app.middleware.cors import setup_cors
# from app.settings import settings 

app = FastAPI()

# Hook up your CORS configurations
setup_cors(app, environment="prod", origins=["https://my-app.com"])
```
