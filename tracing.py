"""
OpenTelemetry Distributed Tracing for ResearchRAG Pro

Implements trace IDs across all services for request correlation and debugging.
Integrates with Jaeger for visualization.
"""

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.pymilvus import PyMilvusInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXInstrumentor
from opentelemetry.trace import Status, StatusCode
from functools import wraps
import logging
import json
from typing import Any, Dict, Optional
from contextvars import ContextVar

# ========================================
# CONFIGURATION
# ========================================

# Context variable for trace ID propagation
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


def setup_tracing(
    service_name: str = "research-rag-backend",
    jaeger_host: str = "jaeger",
    jaeger_port: int = 6831,
    environment: str = "production"
):
    """Initialize OpenTelemetry tracing with Jaeger exporter."""
    
    # Create resource with service information
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
        "deployment.environment": environment,
    })
    
    # Configure Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name=jaeger_host,
        agent_port=jaeger_port,
    )
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(jaeger_exporter)
    provider.add_span_processor(processor)
    
    # Set as global tracer provider
    trace.set_tracer_provider(provider)
    
    # Auto-instrument frameworks
    FastAPIInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    RedisInstrumentor().instrument()
    HTTPXInstrumentor().instrument()
    
    # Custom instrumentation for Milvus (if available)
    try:
        PyMilvusInstrumentor().instrument()
    except:
        pass
    
    logging.info(f"OpenTelemetry tracing initialized for {service_name}")


# ========================================
# TRACER INSTANCE
# ========================================

tracer = trace.get_tracer(__name__)


# ========================================
# STRUCTURED LOGGING WITH TRACE CONTEXT
# ========================================

class TraceContextFilter(logging.Filter):
    """Add trace_id and user_id to all log records."""
    
    def filter(self, record):
        # Get current span context
        span = trace.get_current_span()
        span_context = span.get_span_context()
        
        if span_context.is_valid:
            record.trace_id = format(span_context.trace_id, '032x')
            record.span_id = format(span_context.span_id, '016x')
        else:
            record.trace_id = "none"
            record.span_id = "none"
        
        # Add user ID from context
        record.user_id = user_id_var.get() or "anonymous"
        
        return True


def setup_structured_logging():
    """Configure JSON structured logging with trace context."""
    
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "trace_id": getattr(record, 'trace_id', 'none'),
                "span_id": getattr(record, 'span_id', 'none'),
                "user_id": getattr(record, 'user_id', 'anonymous'),
            }
            
            # Add exception info if present
            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)
            
            # Add extra fields
            if hasattr(record, 'extra'):
                log_data.update(record.extra)
            
            return json.dumps(log_data)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Add trace context filter
    trace_filter = TraceContextFilter()
    logger.addFilter(trace_filter)
    
    # JSON handler for structured logs
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)


# ========================================
# DECORATORS FOR TRACING
# ========================================

def trace_rag_component(component_name: str, operation: str):
    """Decorator to trace RAG pipeline components."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(
                f"{component_name}.{operation}",
                attributes={
                    "component": component_name,
                    "operation": operation,
                }
            ) as span:
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(
                f"{component_name}.{operation}",
                attributes={
                    "component": component_name,
                    "operation": operation,
                }
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def trace_with_attributes(**attributes):
    """Decorator to add custom attributes to span."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            span = trace.get_current_span()
            for key, value in attributes.items():
                span.set_attribute(key, value)
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            span = trace.get_current_span()
            for key, value in attributes.items():
                span.set_attribute(key, value)
            return func(*args, **kwargs)
        
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# ========================================
# RAG PIPELINE TRACING
# ========================================

@trace_rag_component("document_parser", "extract_text")
async def trace_document_parsing(paper_id: str, page_count: int):
    """Example: Trace document parsing."""
    span = trace.get_current_span()
    span.set_attribute("paper_id", paper_id)
    span.set_attribute("page_count", page_count)
    # ... actual parsing logic


@trace_rag_component("math_extractor", "extract_equations")
async def trace_math_extraction(chunk_id: str, equation_count: int):
    """Example: Trace math equation extraction."""
    span = trace.get_current_span()
    span.set_attribute("chunk_id", chunk_id)
    span.set_attribute("equation_count", equation_count)
    # ... actual extraction logic


@trace_rag_component("vector_db", "dense_search")
async def trace_vector_search(query: str, top_k: int, latency_ms: float):
    """Example: Trace vector database search."""
    span = trace.get_current_span()
    span.set_attribute("query_length", len(query))
    span.set_attribute("top_k", top_k)
    span.set_attribute("latency_ms", latency_ms)
    # ... actual search logic


@trace_rag_component("llm", "generate_answer")
async def trace_llm_generation(
    prompt_tokens: int,
    completion_tokens: int,
    model: str
):
    """Example: Trace LLM answer generation."""
    span = trace.get_current_span()
    span.set_attribute("prompt_tokens", prompt_tokens)
    span.set_attribute("completion_tokens", completion_tokens)
    span.set_attribute("model", model)
    # ... actual generation logic


# ========================================
# REQUEST LOGGING WITH SANITIZATION
# ========================================

def sanitize_request_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive information from request data."""
    
    SENSITIVE_KEYS = {
        'api_key', 'password', 'token', 'secret', 'authorization',
        'x-api-key', 'bearer', 'auth', 'credentials'
    }
    
    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        # Redact sensitive keys
        if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
            sanitized[key] = "[REDACTED]"
        
        # Recursively sanitize nested dicts
        elif isinstance(value, dict):
            sanitized[key] = sanitize_request_data(value)
        
        # Sanitize lists
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_request_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        
        # Keep other values
        else:
            sanitized[key] = value
    
    return sanitized


async def log_rag_request(
    user_id: str,
    query: str,
    retrieval_mode: str,
    top_k: int,
    latency_ms: float,
    chunk_count: int,
    faithfulness_score: Optional[float] = None
):
    """Log RAG pipeline request with trace context."""
    
    logger = logging.getLogger(__name__)
    
    # Get trace ID from current span
    span = trace.get_current_span()
    span_context = span.get_span_context()
    trace_id = format(span_context.trace_id, '032x') if span_context.is_valid else "none"
    
    # Sanitize query (truncate, remove PII)
    sanitized_query = query[:200] + "..." if len(query) > 200 else query
    
    logger.info(
        "RAG request processed",
        extra={
            "trace_id": trace_id,
            "user_id": user_id,
            "query_length": len(query),
            "query_preview": sanitized_query,
            "retrieval_mode": retrieval_mode,
            "top_k": top_k,
            "latency_ms": latency_ms,
            "chunk_count": chunk_count,
            "faithfulness_score": faithfulness_score,
        }
    )


async def log_ingestion_event(
    user_id: str,
    paper_id: str,
    source: str,
    page_count: int,
    chunk_count: int,
    math_equation_count: int,
    latency_ms: float,
    status: str
):
    """Log paper ingestion event."""
    
    logger = logging.getLogger(__name__)
    
    span = trace.get_current_span()
    span_context = span.get_span_context()
    trace_id = format(span_context.trace_id, '032x') if span_context.is_valid else "none"
    
    logger.info(
        "Paper ingestion event",
        extra={
            "trace_id": trace_id,
            "user_id": user_id,
            "paper_id": paper_id,
            "source": source,
            "page_count": page_count,
            "chunk_count": chunk_count,
            "math_equation_count": math_equation_count,
            "latency_ms": latency_ms,
            "status": status,
        }
    )


# ========================================
# FASTAPI MIDDLEWARE FOR TRACING
# ========================================

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware to add trace context to requests."""
    
    async def dispatch(self, request: Request, call_next):
        # Extract or generate trace ID
        trace_id = request.headers.get("X-Trace-Id")
        if not trace_id:
            span = trace.get_current_span()
            span_context = span.get_span_context()
            if span_context.is_valid:
                trace_id = format(span_context.trace_id, '032x')
        
        # Store in context var
        if trace_id:
            trace_id_var.set(trace_id)
        
        # Extract user ID from auth
        user_id = request.headers.get("X-User-Id") or "anonymous"
        user_id_var.set(user_id)
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        latency = (time.time() - start_time) * 1000
        
        # Add trace ID to response headers
        if trace_id:
            response.headers["X-Trace-Id"] = trace_id
        
        # Log request
        logger = logging.getLogger(__name__)
        logger.info(
            "HTTP request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": latency,
                "user_id": user_id,
            }
        )
        
        return response


# ========================================
# USAGE EXAMPLE
# ========================================

"""
# In main.py:

from app.tracing import (
    setup_tracing,
    setup_structured_logging,
    TracingMiddleware,
    trace_rag_component
)

# Initialize on startup
setup_tracing(
    service_name="research-rag-backend",
    jaeger_host=os.getenv("JAEGER_HOST", "jaeger"),
    environment=os.getenv("ENVIRONMENT", "production")
)
setup_structured_logging()

# Add middleware
app.add_middleware(TracingMiddleware)

# Use in endpoints:

@app.post("/api/v1/search")
@trace_rag_component("api", "search")
async def search(request: SearchRequest):
    # Automatically traced with span
    results = await perform_search(request.query)
    return results
"""
