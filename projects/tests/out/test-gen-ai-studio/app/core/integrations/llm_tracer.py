import logging
import os
from langfuse import LangFuse

from core.config import settings

logger = logging.getLogger(__name__)

def init_llm_tracer():
    global langfuse
    # Usually LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, and LANGFUSE_HOST are set in env
    host = getattr(settings, "LANGFUSE_HOST", "http://langfuse:3000")
    
    # We initialize only if keys are present, otherwise it logs a warning
    if os.getenv("LANGFUSE_SECRET_KEY"):
        langfuse = LangFuse(
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            host=host
        )
        logger.info("LangFuse tracer connected.")
    else:
        logger.info("LangFuse Keys not set. Tracing is bypassed.")

def trace_llm_call(trace_name: str, request_input: str, response_output: str, request: any = None):
    """Log a full LLM trace to LangFuse."""
    if not langfuse:
        return
        
    try:

        trace = langfuse.trace(
            name=trace_name,
            metadata={"model": "vllm"}
        )
        
        # Log the actual generation block
        trace.generation(
            name="llm_generation",
            model="vllm",
            input=request_input,
            output=response_output,
        )
        
        # In a real background setup we might batch flush, but Python SDK handles this
        logger.debug(f"Traced LLM call: {trace_name}")
    except Exception as e:
        logger.warning(f"Failed to record LangFuse trace: {e}")
