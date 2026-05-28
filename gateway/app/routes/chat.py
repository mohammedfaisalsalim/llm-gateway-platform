import time
import os
import yaml
from pathlib import Path
from fastapi import APIRouter, Header, HTTPException
from app.models import ChatCompletionRequest, StandardResponse
from app.classifier import predict_complexity_tier
from app.database import log_request_to_db
from app.rate_limiter import limiter
from app.providers import send_request
from app.metrics import GATEWAY_ROUTING_DECISIONS, GATEWAY_BUDGET_EVENTS

router = APIRouter(prefix="/v1", tags=["Inference"])

# Dynamic configuration file system discovery mapping
CONFIG_PATH = Path(__file__).parent.parent / "models_config.yaml"

def load_models_config() -> dict:
    """Path-safe localized runtime configurations mapper."""
    try:
        with open(CONFIG_PATH, "r") as file:
            return yaml.safe_load(file)
    except Exception as e:
        raise RuntimeError(f"Failed to read models configuration metadata definitions: {str(e)}")

@router.post("/chat/completions", response_model=StandardResponse)
async def chat_completions(
    body: ChatCompletionRequest,
    x_team_id: str = Header(..., alias="X-Team-Id")
):
    """
    Unified AI Production Gateway Framework Interface.
    Orchestrates real-time traffic shaper tokens, budget quotas, 
    and predictive network routing patterns across localized and remote cloud nodes.
    """
    user_content = body.messages[-1].content if body.messages else ""
    
    # 1. Traffic Shaper Layer (Sliding Window Security Limiter)
    is_limited, retry_after = await limiter.is_rate_limited(x_team_id)
    if is_limited:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Please back off and retry after {retry_after} seconds."
        )

    # 2. Financial Guardrail Verification Layer (Daily Budget Allocation Control)
    budget_key = f"budget:{x_team_id}:daily_usd"
    current_spend = await limiter.redis.get(budget_key)
    current_spend_val = float(current_spend) if current_spend else 0.0
    
    if current_spend_val >= 5.00:  # Enforce default system budget ceiling limits
        GATEWAY_BUDGET_EVENTS.labels(team_id=x_team_id, event_type="exceeded").inc()
        raise HTTPException(
            status_code=402,
            detail=f"Payment Required: Multi-tenant organizational group allocation '{x_team_id}' has exhausted its maximum daily threshold budget ($5.00 limit)."
        )
    elif current_spend_val >= 4.00:  # 80% Soft Warning Notification Tracker
        GATEWAY_BUDGET_EVENTS.labels(team_id=x_team_id, event_type="warning").inc()

    # 3. Machine Learning Cognitive Evaluation Layer
    tier = predict_complexity_tier(user_content)
    config_matrix = load_models_config()["models"]

    # 4. Deterministic Tier-to-Model Mapping Logic
    if tier == 0:
        model_key = "llama3.2"
    elif tier == 1:
        model_key = "gemini-flash"
    else:
        model_key = "mistral"

    # Track structural routing classification decisions metrics inside Prometheus
    GATEWAY_ROUTING_DECISIONS.labels(model_tier=f"Tier_{tier}", assigned_key=model_key).inc()
    
    cfg = config_matrix[model_key]

    # 5. Non-Blocking Outbound Execution Proxy Handover
    response_payload = await send_request(
        prompt=user_content,
        provider=cfg["provider"],
        model_id=cfg["model_id"],
        cost_per_input=cfg["cost_per_input_token"],
        cost_per_output=cfg["cost_per_output_token"],
        current_key=model_key,
        config_data=config_matrix
    )

    # 6. Accumulate Running Ledger Balances
    if response_payload.cost_usd > 0:
        async with limiter.redis.pipeline(transaction=True) as pipe:
            pipe.incrbyfloat(budget_key, response_payload.cost_usd)
            # Set rolling timeout sequence tracking to clear out balances at standard midnight intervals
            pipe.expire(budget_key, 86400)
            await pipe.execute()

    # 7. Safe Thread-Isolated Database Logging Handover
    log_request_to_db(
        team_id=x_team_id,
        model_used=response_payload.model_used,
        latency_ms=response_payload.latency_ms,
        prompt_tokens=response_payload.prompt_tokens,
        completion_tokens=response_payload.completion_tokens,
        total_tokens=response_payload.total_tokens,
        cost_usd=response_payload.cost_usd
    )

    return response_payload