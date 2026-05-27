import yaml
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Header, Response
from app.models import ChatCompletionRequest
from app.providers import send_request
from app.classifier import classifier
from app.database import log_request_to_db
from app.rate_limiter import limiter  
from app.config import settings
from app.metrics import GATEWAY_ROUTING_DECISIONS, GATEWAY_BUDGET_EVENTS  # ← Import metrics

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

CONFIG_PATH = Path(__file__).parent.parent / "models_config.yaml"

with open(CONFIG_PATH, "r") as f: 
    config_data = yaml.safe_load(f)["models"]

@router.post("/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest, 
    response: Response,
    x_team_id: str = Header(default="default-team")  
):
    # --- DAY 8 PROTECTION RADAR CHECK (SLIDING WINDOW) ---
    is_limited, retry_after = await limiter.is_rate_limited(x_team_id)
    if is_limited:
        response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=429, 
            detail={"error": "Too Many Requests", "retry_after_seconds": retry_after}
        )
        
    # --- DAY 10 FINANCIAL BUDGET CONTROL GUARDRAIL ---
    current_spend = 0.0
    try:
        cached_spend = await limiter.redis.get(f"budget:spend:{x_team_id}")
        current_spend = float(cached_spend) if cached_spend is not None else 0.0
        
        # 1. Hard Cutoff Interception Block
        if current_spend >= settings.DEFAULT_DAILY_BUDGET_USD:
            # Record budget breach event metric
            GATEWAY_BUDGET_EVENTS.labels(team_id=x_team_id, event_type="exceeded").inc()
            raise HTTPException(
                status_code=402,  
                detail={
                    "error": "Budget Exceeded",
                    "team_id": x_team_id,
                    "current_daily_spend_usd": current_spend,
                    "allowed_daily_budget_usd": settings.DEFAULT_DAILY_BUDGET_USD,
                    "message": "Daily budget threshold breached. Access denied until tomorrow."
                }
            )
            
        # 2. Early Warning Detection Flag (80%+ Budget Consumed)
        warning_threshold = settings.DEFAULT_DAILY_BUDGET_USD * 0.80
        if current_spend >= warning_threshold:
            # Record budget warning metric
            GATEWAY_BUDGET_EVENTS.labels(team_id=x_team_id, event_type="warning").inc()
            
            pct_used = (current_spend / settings.DEFAULT_DAILY_BUDGET_USD) * 100
            pct_remaining = 100.0 - pct_used
            response.headers["X-Budget-Warning"] = (
                f"{pct_remaining:.1f}% daily budget remaining "
                f"(${current_spend:.4f} of ${settings.DEFAULT_DAILY_BUDGET_USD:.2f} used)"
            )
            
    except HTTPException as budget_err:
        raise budget_err
    except Exception as e:
        logger.error(f"Budget Engine Degraded: {str(e)}")

    # --- INFERENCE & EXECUTION LAYER ---
    try:
        user_prompt = request.messages[-1].content if request.messages else ""
        tier = classifier.predict_tier(user_prompt)
        
        if tier == 0:
            key = "llama3.2"
        elif tier == 1:
            key = "gemini-flash"
        else:
            key = "mistral"
            
        # Record classifier routing choice event metric
        GATEWAY_ROUTING_DECISIONS.labels(model_tier=f"Tier {tier}", assigned_key=key).inc()
            
        cfg = config_data[key]
        
        res = await send_request(
            prompt=user_prompt,
            provider=cfg["provider"],
            model_id=cfg["model_id"],
            cost_per_input=cfg["cost_per_input_token"],
            cost_per_output=cfg["cost_per_output_token"],
            current_key=key,
            config_data=config_data  
        )
        
        await log_request_to_db(
            prompt=user_prompt,
            model=res.model_used,
            latency=res.latency_ms,
            tokens=res.total_tokens,
            cost=res.cost_usd,
            output=res.output_text
        )
        
        # 4. Real-Time Tracking & Absolute Wall-Clock Expiry Enforcement
        if res.cost_usd > 0:
            redis_key = f"budget:spend:{x_team_id}"
            await limiter.redis.incrbyfloat(redis_key, res.cost_usd)
            
            now_utc = datetime.now(timezone.utc)
            seconds_until_midnight = max(1, (
                86400
                - (now_utc.hour * 3600)
                - (now_utc.minute * 60)
                - now_utc.second
            ))
            await limiter.redis.expire(redis_key, seconds_until_midnight)
        
        return {
            "id": f"gw-cmpl-{int(time.time() * 1000)}",
            "object": "chat.completion",
            "model": res.model_used,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": res.output_text
                },
                "finish_reason": "stop"
            }],
            "infrastructure_metadata": {
                "computed_complexity_tier": tier,
                "routing_key_assigned": key,
                "execution_latency_ms": res.latency_ms,
                "estimated_cost_usd": res.cost_usd
            }
        }
    except HTTPException as status_err: 
        if "X-Budget-Warning" in response.headers:
            if status_err.headers is None:
                status_err.headers = {}
            status_err.headers["X-Budget-Warning"] = response.headers["X-Budget-Warning"]
        raise status_err
    except Exception as e: 
        headers = {}
        if "X-Budget-Warning" in response.headers:
            headers["X-Budget-Warning"] = response.headers["X-Budget-Warning"]
        raise HTTPException(status_code=502, detail=str(e), headers=headers)