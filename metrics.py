"""
Prometheus metrics instrumentation for ResearchRAG Pro

Custom metrics for RAGAS quality, math accuracy, and latency tracking.
"""

from prometheus_client import Counter, Histogram, Gauge, Summary
from functools import wraps
import time
from typing import Callable, Any


# ========================================
# RAGAS QUALITY METRICS
# ========================================

# Faithfulness: How well answers are grounded in retrieved context
ragas_faithfulness = Gauge(
    'ragas_faithfulness',
    'RAGAS faithfulness score (groundedness of answers)',
    ['model', 'retrieval_mode']
)

# Answer relevancy: How relevant answers are to questions
ragas_answer_relevancy = Gauge(
    'ragas_answer_relevancy',
    'RAGAS answer relevancy score',
    ['model', 'retrieval_mode']
)

# Context precision: Signal-to-noise ratio of retrieved context
ragas_context_precision = Gauge(
    'ragas_context_precision',
    'RAGAS context precision score',
    ['retrieval_mode']
)

# Context recall: Coverage of ground truth in retrieved context
ragas_context_recall = Gauge(
    'ragas_context_recall',
    'RAGAS context recall score',
    ['retrieval_mode']
)

# ========================================
# MATH RENDERING METRICS
# ========================================

# Math equation accuracy (LaTeX → rendered)
rag_math_equation_accuracy = Gauge(
    'rag_math_equation_accuracy',
    'Percentage of equations rendered correctly'
)

# Math extraction success rate
rag_math_extraction_success = Counter(
    'rag_math_extraction_total',
    'Total math equations extracted from papers',
    ['extraction_method', 'status']
)

# ========================================
# SEARCH & RETRIEVAL METRICS
# ========================================

# Search request counters
rag_search_requests_total = Counter(
    'rag_search_requests_total',
    'Total search requests',
    ['retrieval_mode', 'status']
)

# Search latency histogram
rag_search_duration_seconds = Histogram(
    'rag_search_duration_seconds',
    'Search request latency in seconds',
    ['retrieval_mode'],
    buckets=[0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
)

# Retrieval recall metrics
rag_retrieval_recall_at_10 = Gauge(
    'rag_retrieval_recall_at_10',
    'Retrieval recall@10 score',
    ['retrieval_type']
)

# Number of results returned
rag_search_results_count = Histogram(
    'rag_search_results_count',
    'Number of search results returned',
    buckets=[0, 1, 5, 10, 20, 50, 100]
)

# Search errors
rag_search_errors_total = Counter(
    'rag_search_errors_total',
    'Total search errors',
    ['error_type', 'retrieval_mode']
)

# ========================================
# INGESTION METRICS
# ========================================

# Papers ingested
rag_papers_ingested_total = Counter(
    'rag_papers_ingested_total',
    'Total papers successfully ingested',
    ['source']
)

# Ingestion duration
rag_ingestion_duration_seconds = Histogram(
    'rag_ingestion_duration_seconds',
    'Paper ingestion latency in seconds',
    ['source'],
    buckets=[1, 5, 10, 20, 30, 60, 120, 300, 600]
)

# Chunks created per paper
rag_chunks_per_paper = Histogram(
    'rag_chunks_per_paper',
    'Number of chunks created per paper',
    buckets=[10, 50, 100, 200, 500, 1000, 2000]
)

# Ingestion errors
rag_ingestion_errors_total = Counter(
    'rag_ingestion_errors_total',
    'Total ingestion errors',
    ['error_type', 'source']
)

# ========================================
# PERFORMANCE METRICS
# ========================================

# Vector embedding latency
rag_embedding_duration_seconds = Histogram(
    'rag_embedding_duration_seconds',
    'Time to generate embeddings',
    ['model'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

# LLM generation latency
rag_llm_generation_duration_seconds = Histogram(
    'rag_llm_generation_duration_seconds',
    'Time for LLM to generate answers',
    ['model'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0]
)

# Database query latency
rag_db_query_duration_seconds = Histogram(
    'rag_db_query_duration_seconds',
    'Database query latency',
    ['database', 'operation'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
)

# ========================================
# COST METRICS
# ========================================

# OpenAI API costs
rag_openai_api_cost_usd_total = Counter(
    'rag_openai_api_cost_usd_total',
    'Total OpenAI API costs in USD',
    ['model', 'operation']
)

# Token usage
rag_tokens_used_total = Counter(
    'rag_tokens_used_total',
    'Total tokens consumed',
    ['model', 'token_type']  # token_type: input, output
)

# ========================================
# RATE LIMITING METRICS
# ========================================

rag_rate_limit_triggered_total = Counter(
    'rag_rate_limit_triggered_total',
    'Number of times rate limit was triggered',
    ['endpoint', 'limit_type']
)

# ========================================
# DECORATORS FOR EASY INSTRUMENTATION
# ========================================

def track_search_latency(retrieval_mode: str):
    """Decorator to track search latency."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                rag_search_requests_total.labels(
                    retrieval_mode=retrieval_mode,
                    status='success'
                ).inc()
                return result
            except Exception as e:
                rag_search_requests_total.labels(
                    retrieval_mode=retrieval_mode,
                    status='error'
                ).inc()
                rag_search_errors_total.labels(
                    error_type=type(e).__name__,
                    retrieval_mode=retrieval_mode
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                rag_search_duration_seconds.labels(
                    retrieval_mode=retrieval_mode
                ).observe(duration)
        return wrapper
    return decorator


def track_ingestion_latency(source: str):
    """Decorator to track ingestion latency."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                rag_papers_ingested_total.labels(source=source).inc()
                return result
            except Exception as e:
                rag_ingestion_errors_total.labels(
                    error_type=type(e).__name__,
                    source=source
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                rag_ingestion_duration_seconds.labels(source=source).observe(duration)
        return wrapper
    return decorator


def track_db_query(database: str, operation: str):
    """Decorator to track database query latency."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start_time
                rag_db_query_duration_seconds.labels(
                    database=database,
                    operation=operation
                ).observe(duration)
        return wrapper
    return decorator


# ========================================
# UTILITY FUNCTIONS
# ========================================

def record_ragas_metrics(
    faithfulness: float,
    answer_relevancy: float,
    context_precision: float,
    context_recall: float,
    model: str = "gpt-4",
    retrieval_mode: str = "hybrid"
):
    """Record RAGAS evaluation metrics."""
    ragas_faithfulness.labels(
        model=model,
        retrieval_mode=retrieval_mode
    ).set(faithfulness)
    
    ragas_answer_relevancy.labels(
        model=model,
        retrieval_mode=retrieval_mode
    ).set(answer_relevancy)
    
    ragas_context_precision.labels(
        retrieval_mode=retrieval_mode
    ).set(context_precision)
    
    ragas_context_recall.labels(
        retrieval_mode=retrieval_mode
    ).set(context_recall)


def record_openai_cost(
    model: str,
    operation: str,
    input_tokens: int,
    output_tokens: int
):
    """Record OpenAI API costs based on token usage."""
    
    # Pricing as of Jan 2024 (update as needed)
    pricing = {
        "gpt-4": {"input": 0.03 / 1000, "output": 0.06 / 1000},
        "gpt-3.5-turbo": {"input": 0.0015 / 1000, "output": 0.002 / 1000},
        "text-embedding-ada-002": {"input": 0.0001 / 1000, "output": 0},
    }
    
    if model not in pricing:
        return
    
    cost = (
        input_tokens * pricing[model]["input"] +
        output_tokens * pricing[model]["output"]
    )
    
    rag_openai_api_cost_usd_total.labels(
        model=model,
        operation=operation
    ).inc(cost)
    
    rag_tokens_used_total.labels(
        model=model,
        token_type="input"
    ).inc(input_tokens)
    
    rag_tokens_used_total.labels(
        model=model,
        token_type="output"
    ).inc(output_tokens)


# ========================================
# EXAMPLE USAGE
# ========================================

"""
from app.metrics import (
    track_search_latency,
    track_ingestion_latency,
    record_ragas_metrics,
    rag_search_results_count
)

# In your search endpoint:
@track_search_latency(retrieval_mode="hybrid")
async def search(query: str, top_k: int = 10):
    results = await vector_search(query, top_k)
    rag_search_results_count.observe(len(results))
    return results

# In your ingestion pipeline:
@track_ingestion_latency(source="arxiv")
async def ingest_paper(paper_id: str):
    chunks = await parse_and_chunk(paper_id)
    rag_chunks_per_paper.observe(len(chunks))
    return chunks

# In your evaluation pipeline:
def run_evaluation():
    results = evaluate_rag_system()
    record_ragas_metrics(
        faithfulness=results.faithfulness,
        answer_relevancy=results.answer_relevancy,
        context_precision=results.context_precision,
        context_recall=results.context_recall
    )
"""
