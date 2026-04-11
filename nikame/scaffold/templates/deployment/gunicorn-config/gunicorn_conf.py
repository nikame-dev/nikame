import multiprocessing
import os

# ---------------------------------------------------------
# Gunicorn Production Configuration
# ---------------------------------------------------------

# Bind to internal container port
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Use the Uvicorn worker class for FastAPI
worker_class = "uvicorn.workers.UvicornWorker"

# Dynamic worker calculation: (2 x cores) + 1 is the standard formula.
# However, for AI services, you might want fewer workers to avoid VRAM OOM.
workers_per_core = float(os.getenv("WORKERS_PER_CORE", "1"))
default_web_concurrency = workers_per_core * multiprocessing.cpu_count() + 1
workers = int(os.getenv("WEB_CONCURRENCY", default_web_concurrency))

# Timeout: AI models can take a long time. 
# Increase this if you have high latency inference.
timeout = int(os.getenv("TIMEOUT", "120"))
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stdout
loglevel = os.getenv("LOG_LEVEL", "info")

# Process Naming
proc_name = "fastapi-app"
