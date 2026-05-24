import yaml
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.models import ChatCompletionRequest, ChatMessage
from app.providers import send_request
from app.classifier import classifier
from app.database import log_request_to_db

router = APIRouter()

# Resolve absolute workspace directory dynamically to prevent container/root paths from breaking
CONFIG_PATH = Path(__file__).parent.parent / "models_config.yaml"

with open(CONFIG_PATH, "r") as f: 
    config_data = yaml.safe_load(f)["models"]

@router.post("/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
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
        
        # Generate a unique dynamic transaction ID mapping directly to the current epoch timestamp
        unique_id = f"gw-cmpl-{int(time.time() * 1000)}"
        
        return {
            "id": unique_id,
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