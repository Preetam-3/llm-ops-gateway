from prometheus_client import Counter, Histogram, Gauge

llm_request_total = Counter(
    "llm_request_total",
    "Total LLM requests by model and status",
    labelnames=["model", "status"],
)

llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM request latency in seconds",
    labelnames=["model"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total tokens used by model and type (prompt/completion)",
    labelnames=["model", "type"],
)

llm_estimated_cost_dollars = Gauge(
    "llm_estimated_cost_dollars",
    "Estimated cost per request by model",
    labelnames=["model"],
)

llm_rate_limited_total = Counter(
    "llm_rate_limited_total",
    "Total rate-limited requests",
)
