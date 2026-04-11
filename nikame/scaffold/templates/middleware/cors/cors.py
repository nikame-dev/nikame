from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# In a real environment, read these out of pydantic BaseSettings
ENVIRONMENT = "dev"
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",  # Vite default
    "https://production-frontend.com"
]

def setup_cors(app: FastAPI, environment: str = ENVIRONMENT, origins: list[str] = ALLOWED_ORIGINS) -> None:
    """
    Hooks up CORS configurations with smart defaults depending on if we are in
    dev, staging, or prod.
    """
    
    if environment == "dev":
        # Dev gets wide open access for easy front-end hooking
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        # Prod locks down to just the supplied allowed origins
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
        )
