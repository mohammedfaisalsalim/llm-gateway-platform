from prometheus_client import Counter

# 1. Track which model variant receives traffic
GATEWAY_ROUTING_DECISIONS = Counter(
    "gateway_routing_decisions_total",
    "Total number of routing decisions made by the classifier model",
    ["model_tier", "assigned_key"]
)

# 2. Track architectural circuit breaker state changes
GATEWAY_CIRCUIT_TRIPS = Counter(
    "gateway_circuit_trips_total",
    "Total number of times a provider circuit breaker was tripped open",
    ["provider_key"]
)

# 3. Track daily financial milestone events
GATEWAY_BUDGET_EVENTS = Counter(
    "gateway_budget_events_total",
    "Total number of financial cap events triggered",
    ["team_id", "event_type"]  # event_type: 'warning' or 'exceeded'
)

# 4. Track adaptive fallback routing depth counts
GATEWAY_FAILOVER_HOPS = Counter(
    "gateway_failover_hops_total",
    "Total number of cascading provider hops executed across the routing ring",
    ["initial_key", "fallback_key"]
)