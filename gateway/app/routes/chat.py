import yaml
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException, Header, Response
from app.models import ChatCompletionRequest
from app.providers import send_request
from app.classifier import classifier
from app.database import log_request_to_db
from app.rate_limiter import limiter  # Import our new rate limiting engine singleton

router = APIRouter()

CONFIG_PATH = Path(__file__).parent.parent / "models_config.yaml"

with open(CONFIG_PATH, "r") as f: 
    config_data = yaml.safe_load(f)["models"]

@router.post("/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest, 
    response: Response,
    x_team_id: str = Header(default="default-team")  # Capture calling identity via HTTP headers
):
    # --- DAY 8 PROTECTION RADAR CHECK ---
    is_limited, retry_after = await limiter.is_rate_limited(x_team_id)
    if is_limited:
        # Inject standard compliance header alerting upstream caller frameworks when to back off
        response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=429, 
            detail={"error": "Too Many Requests", "retry_after_seconds": retry_after}
        )
    # ------------------------------------

    try:
        user_prompt = request.messages[-1].content if request.messages else ""
        
        # 1. Determine prompt complexity tier via Scikit-learn singleton model weights
        tier = classifier.predict_tier(user_prompt)
        
        # 2. Dynamic map routing using the integer tier outputs (0, 1, 2)
        if tier == 0:
            key = "llama3.2"
        elif tier == 1:
            key = "gemini-flash"
        else:
            key = "mistral"
            
        cfg = config_data[key]
        
        # 3. Request execution using non-blocking async-thread worker allocations
        res = await send_request(
            prompt=user_prompt,
            provider=cfg["provider"],
            model_id=cfg["model_id"],
            cost_per_input=cfg["cost_per_input_token"],
            cost_per_output=cfg["cost_per_output_token"]
        )
        
        # 4. Record transactional history logs to the SQLite backend using a thread worker
        await log_request_to_db(
            prompt=user_prompt,
            model=res.model_used,
            latency=res.latency_ms,
            tokens=res.total_tokens,
            cost=res.cost_usd,
            output=res.output_text
        )
        
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
        raise status_err
    except Exception as e: 
        raise HTTPException(status_code=500, detail=str(e))