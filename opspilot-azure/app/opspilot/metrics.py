"""Prometheus metrics for the RAG pipeline (LLM latency, tokens, errors, guardrails, retrieval)."""

from prometheus_client import Counter, Histogram

REQUESTS = Counter("opspilot_requests_total", "HTTP requests handled", ["endpoint", "status"])

LLM_LATENCY = Histogram(
    "opspilot_llm_latency_seconds",
    "Latency of LLM calls",
    ["operation", "model"],  # operation = chat | embed
    buckets=(0.1, 0.25, 0.5, 1, 2, 4, 8, 16, 32),
)
LLM_TOKENS = Counter("opspilot_llm_tokens_total", "Tokens used", ["model", "type"])  # type = prompt | completion
LLM_ERRORS = Counter("opspilot_llm_errors_total", "Failed LLM calls", ["operation", "model"])

GUARDRAIL_BLOCKS = Counter("opspilot_guardrail_blocks_total", "Requests blocked by guardrails", ["reason"])
REDACTIONS = Counter("opspilot_redactions_total", "Secrets redacted from answers or documents", ["kind"])

RETRIEVAL_DISTANCE = Histogram(
    "opspilot_retrieval_best_distance",
    "Cosine distance of the best matching chunk (lower = more relevant)",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0),
)
NO_CONTEXT = Counter("opspilot_no_context_total", "Questions with no relevant runbook found")
