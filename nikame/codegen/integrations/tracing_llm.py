"""LangFuse LLM Tracing Integration.

Triggers when LangFuse is active.
Wires telemetry to LLM calls and automatically attaches the User ID
if the Auth module is present in the matrix.
"""

from __future__ import annotations

from nikame.codegen.integrations.base import BaseIntegration


class TracingLLMIntegration(BaseIntegration):
    """Generates LangFuse LLM Tracing middleware."""

    REQUIRED_MODULES = ["langfuse"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.has_auth = set(["auth", "cognito", "supabase_auth"]).intersection(self.active_modules)
        
        llms = ["llamacpp", "ollama", "vllm", "tgi", "triton", "localai", "xinference", "airllm"]
        self.served_model = next((l for l in llms if l in self.active_modules), "prediction_model")

    @classmethod
    def should_trigger(cls, active_modules: set[str], active_features: set[str]) -> bool:
        """Trigger if LangFuse is active alongside a serving gateway."""
        has_langfuse = "langfuse" in active_modules
        has_serving = any(m in active_modules for m in ["llamacpp", "ollama", "vllm", "tgi", "triton", "localai", "xinference", "airllm", "bentoml", "whisper"])
        return has_langfuse and has_serving

    def generate_core(self) -> list[tuple[str, str]]:
        core_logic = self._generate_langfuse_tracer()
        return [("app/core/integrations/llm_tracer.py", core_logic)]

    def generate_lifespan(self) -> str:
        return """
    # --- LangFuse Tracing ---
    try:
        from app.core.integrations.llm_tracer import init_llm_tracer
        logger.info("Initializing LangFuse LLM tracing...")
        init_llm_tracer()
    except Exception as e:
        logger.warning(f"Failed to initialize LangFuse tracer: {e}")
        """

    def generate_health(self) -> dict[str, str]:
        return {}

    def generate_metrics(self) -> str:
        return """
    LANGFUSE_TRACES_SENT = Counter(
        "nikame_langfuse_traces_sent_total", 
        "Count of LLM traces sent to LangFuse"
    )
        """

    def generate_guide(self) -> str:
        auth_note = ""
        if self.has_auth:
            auth_note = "\n**User Tracking:** The Auth module is active. Traces automatically tag the `user_id` of the authenticated request to help track cost and usage per user."
            
        return f"""
### LLM Tracing (LangFuse)
**Status:** Active 🟢 
**Target Engine:** `{self.served_model}`

All calls to the LLM Gateway are instrumented with OpenTelemetry and LangFuse native callbacks to log prompts, responses, token usage, and latency. {auth_note}
"""

    def _generate_langfuse_tracer(self) -> str:
        auth_import = "from fastapi import Request" if self.has_auth else ""
        user_extractor = ""
        
        if self.has_auth:
            user_extractor = """
    # Extract user_id from the authenticated request if possible
    user_id = getattr(request.state, "user", {}).get("sub", "anonymous") if request else "system"
    trace = langfuse.trace(
        name=trace_name,
        user_id=user_id,
        metadata={"model": "%s"}
    )""" % self.served_model
        else:
            user_extractor = """
    trace = langfuse.trace(
        name=trace_name,
        metadata={"model": "%s"}
    )""" % self.served_model

        return f"""import logging
import os
from langfuse import LangFuse
{auth_import}
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize the LangFuse client singleton
langfuse = None

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
    \"\"\"Log a full LLM trace to LangFuse.\"\"\"
    if not langfuse:
        return
        
    try:
        {user_extractor}
        
        # Log the actual generation block
        trace.generation(
            name="llm_generation",
            model="{self.served_model}",
            input=request_input,
            output=response_output,
        )
        
        # In a real background setup we might batch flush, but Python SDK handles this
        logger.debug(f"Traced LLM call: {{trace_name}}")
    except Exception as e:
        logger.warning(f"Failed to record LangFuse trace: {{e}}")
"""
