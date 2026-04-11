import traceback
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

log = structlog.get_logger("app.middleware.error_boundary")

class ErrorBoundaryMiddleware(BaseHTTPMiddleware):
    """
    The final safety net. Any uncaught exceptions that bubble up this far
    have bypassed all FastAPI exception handlers.
    
    If these aren't stripped, Uvicorn will dump a complete Python 
    interactive traceback to the client -- a severe security vulnerability.
    """
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            # First, securely log the raw traceback internally
            log.error(
                "uncaught_global_exception",
                error=str(e),
                traceback=traceback.format_exc(),
                path=request.url.path
            )
            
            # Second, explicitly block the client from seeing it
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": "An unexpected system error occurred. Operations have been safely halted and the engineering team has been notified."
                }
            )
