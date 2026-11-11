from prometheus_client import Counter, Histogram

INVESTIGATIONS = Counter("copilot_investigations_total", "Investigations run", ["status"])  # ok | error | skipped
INVESTIGATION_SECONDS = Histogram(
    "copilot_investigation_duration_seconds", "End-to-end investigation time",
    buckets=(5, 10, 20, 30, 60, 90, 120, 180, 300),
)
TOOL_CALLS = Counter("copilot_tool_calls_total", "MCP tool calls made by the agent", ["tool", "status"])
LLM_LATENCY = Histogram(
    "copilot_llm_latency_seconds", "Latency of one LLM call", ["provider"],
    buckets=(0.25, 0.5, 1, 2, 4, 8, 16, 32, 64),
)
LLM_TOKENS = Counter("copilot_llm_tokens_total", "Tokens used", ["provider", "type"])
LLM_ERRORS = Counter("copilot_llm_errors_total", "Failed LLM calls", ["provider"])
REDACTIONS = Counter("copilot_redactions_total", "Secrets removed from tool output", ["kind"])
