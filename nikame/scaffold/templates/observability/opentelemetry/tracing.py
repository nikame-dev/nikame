import os
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def setup_tracing(app: FastAPI, service_name: str = "fastapi-service"):
    """
    Initializes OpenTelemetry tracing.
    Configures an OTLP exporter to send traces to a collector (like Jaeger or Honeycomb).
    """
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    
    # Set up the tracer provider
    provider = TracerProvider()
    
    # Configure the exporter
    try:
        otlp_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    except Exception:
        # Fallback to console or no-op if exporter fails
        pass
        
    trace.set_tracer_provider(provider)
    
    # Instrument the FastAPI app
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
