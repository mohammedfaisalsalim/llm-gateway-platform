import time
import os
import asyncio
import logging
import ollama
import google.generativeai as genai
from fastapi import HTTPException
from app.models import StandardResponse
from app.rate_limiter import limiter  

logger = logging.getLogger("uvicorn.error")

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

def get_fallback_key(current_key: str) -> str:
    """Deterministic routing loop for provider failovers."""
    mapping = {
        "llama3.2": "gemini-flash",
        "gemini-flash": "mistral",
        "mistral": "llama3.2"
    }
    return mapping.get(current_key, "llama3.2")

async def send_request(
    prompt: str, 
    provider: str, 
    model_id: str, 
    cost_per_input: float, 
    cost_per_output: float, 
    current_key: str, 
    config_data: dict,
    failover_hops: int = 0  
) -> StandardResponse:
    start_time = time.time()
    
    # 0. Global Outage Protection Handbrake
    if failover_hops >= 3:
        logger.critical("🚨 TOTAL GATEWAY SYSTEM ECLIPSE: All downstream provider pathways are completely exhausted!")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Service Unavailable",
                "message": "All upstream LLM engine tiers are currently failing or rate-limited. Please retry later."
            }
        )
    
    # 1. Gemini Configuration Validation Guard
    if provider == "gemini" and not GEMINI_KEY:
        raise HTTPException(
            status_code=501,
            detail=f"Gemini API key is missing from gateway environment configuration."
        )
    
    # 2. Circuit Breaker Pre-Flight Check
    failure_count_key = f"circuit:{current_key}:failures"
    try:
        fail_count = await limiter.redis.get(failure_count_key)
        if fail_count and int(fail_count) >= 5:
            fallback_key = get_fallback_key(current_key)
            logger.warning(f"🚨 CIRCUIT OPEN for '{current_key}'. Skipping execution and jumping to '{fallback_key}'")
            
            cfg = config_data[fallback_key]
            return await send_request(
                prompt=prompt,
                provider=cfg["provider"],
                model_id=cfg["model_id"],
                cost_per_input=cfg["cost_per_input_token"],
                cost_per_output=cfg["cost_per_output_token"],
                current_key=fallback_key,
                config_data=config_data,
                failover_hops=failover_hops + 1  
            )
    except HTTPException as http_err:
        raise http_err
    except Exception as redis_err:
        logger.error(f"Circuit Breaker Cache Lookup Degraded: {str(redis_err)}")

    # 3. Downstream Execution Engine
    output_text, p_tokens, c_tokens = "", 0, 0
    try:
        if provider == "ollama":
            res = await asyncio.to_thread(
                ollama.chat, 
                model=model_id, 
                messages=[{'role': 'user', 'content': prompt}]
            )
            output_text = res['message']['content']
            p_tokens = res.get('prompt_eval_count', len(prompt) // 4)
            c_tokens = res.get('eval_count', len(output_text) // 4)
                
        elif provider == "gemini":
            model = genai.GenerativeModel(model_id)
            res = await asyncio.to_thread(model.generate_content, prompt)
            output_text = res.text
            p_tokens, c_tokens = len(prompt) // 4, len(output_text) // 4

        # Clean recovery state check on success
        try:
            await limiter.redis.delete(failure_count_key)
            await limiter.redis.set(f"circuit:{current_key}:state", "closed")
        except Exception:
            pass

    except Exception as e:
        logger.error(f"❌ Provider Execution Failure on '{current_key}': {str(e)}")
        try:
            # FIX 1: Enforce atomic transactional changes using a secure context manager
            async with limiter.redis.pipeline(transaction=True) as pipe:
                pipe.incr(failure_count_key)
                pipe.expire(failure_count_key, 60)
                results = await pipe.execute()
            
            # Extract the increment results directly from the first index response array element
            current_fails = results[0] if results else 0
            if current_fails and int(current_fails) >= 5:
                await limiter.redis.set(f"circuit:{current_key}:state", "open")
                logger.error(f"💥 FORCED CIRCUIT TRIP: '{current_key}' has crossed 5 failures.")
        except Exception as pipe_err:
            logger.error(f"Failed to record atomic failure metric: {str(pipe_err)}")

        # Move to next fallback with incremented structural hops
        fallback_key = get_fallback_key(current_key)
        cfg = config_data[fallback_key]
        return await send_request(
            prompt=prompt,
            provider=cfg["provider"],
            model_id=cfg["model_id"],
            cost_per_input=cfg["cost_per_input_token"],
            cost_per_output=cfg["cost_per_output_token"],
            current_key=fallback_key,
            config_data=config_data,
            failover_hops=failover_hops + 1  
        )
            
    latency_ms = (time.time() - start_time) * 1000
    return StandardResponse(
        output_text=output_text, 
        prompt_tokens=p_tokens, 
        completion_tokens=c_tokens,
        total_tokens=p_tokens + c_tokens, 
        latency_ms=latency_ms,
        cost_usd=(p_tokens * cost_per_input) + (c_tokens * cost_per_output), 
        model_used=model_id  # FIX 2: Restored to raw string value to prevent analytics labeling fragmentation
    )