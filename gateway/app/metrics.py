from prometheus_client import Counter, Histogram

# ---------- Routing / health (existing) -----------------------------------

GATEWAY_ROUTING_DECISIONS = Counter(
    "gateway_routing_decisions_total",
    "Total number of routing decisions made by the classifier model",
    ["model_tier", "assigned_key"],
)

GATEWAY_CIRCUIT_TRIPS = Counter(
    "gateway_circuit_trips_total",
    "Total number of times a provider circuit breaker was tripped open",
    ["provider_key"],
)

GATEWAY_BUDGET_EVENTS = Counter(
    "gateway_budget_events_total",
    "Total number of financial cap events triggered",
    ["team_id", "event_type"],  # event_type: 'warning' or 'exceeded'
)

GATEWAY_FAILOVER_HOPS = Counter(
    "gateway_failover_hops_total",
    "Total number of cascading provider hops executed across the routing ring",
    ["initial_key", "fallback_key"],
)

# ---------- Token economics (new) -----------------------------------------

GATEWAY_PROMPT_TOKENS = Counter(
    "gateway_prompt_tokens_total",
    "Cumulative prompt tokens consumed per team and model",
    ["team_id", "model_id"],
)

GATEWAY_COMPLETION_TOKENS = Counter(
    "gateway_completion_tokens_total",
    "Cumulative completion tokens generated per team and model",
    ["team_id", "model_id"],
)

# ---------- Cost (new) ----------------------------------------------------

GATEWAY_COST_USD = Counter(
    "gateway_cost_usd_total",
    "Cumulative cost in USD per team and model",
    ["team_id", "model_id"],
)

# ---------- Bandwidth / payload size (new) --------------------------------

GATEWAY_REQUEST_BYTES = Counter(
    "gateway_request_bytes_total",
    "Cumulative bytes received in user prompts (UTF-8)",
    ["team_id", "model_id"],
)

GATEWAY_RESPONSE_BYTES = Counter(
    "gateway_response_bytes_total",
    "Cumulative bytes returned in model responses (UTF-8)",
    ["team_id", "model_id"],
)

# ---------- Inference latency histogram (new) -----------------------------
# Lets us compute p50/p95/p99 latency per model in Grafana.

GATEWAY_INFERENCE_LATENCY = Histogram(
    "gateway_inference_latency_seconds",
    "End-to-end inference latency in seconds, per model",
    ["model_id"],
    buckets=[0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30, 60, 120],
)
