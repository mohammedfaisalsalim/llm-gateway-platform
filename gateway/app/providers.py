import time
import os
import asyncio
import logging
import ollama
import google.generativeai as genai
from fastapi import HTTPException
from app.models import StandardResponse
from app.rate_limiter import limiter  
from app.metrics import GATEWAY_CIRCUIT_TRIPS, GATEWAY_FAILOVER_HOPS

logger = logging.getLogger("uvicorn.error")

# Configure Google Gemini Cloud Tier globally if API key is present
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

def get_fallback_key(current_key: str) -> str:
    """
    Deterministic fallback loop mapping engine to achieve high-availability.
    If an engine fails, it shifts gracefully across tiers in under 10ms.
    Ring: llama3.2 → gemini-flash → llama3.1 → llama3.2 (loops).
    """
    mapping = {
        "llama3.2": "gemini-flash",
        "gemini-flash": "llama3.1",
        "llama3.1": "llama3.2",
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
    """
    Core dynamic request dispatcher featuring a self-healing Circuit Breaker Ring
    and automatic failover hopping mechanics.
    """
    start_time = time.time()
    
    # 1. Total Gateway Circuit Eclipse Handbrake
    if failover_hops >= 3:
        logger.critical("🚨 TOTAL GATEWAY SYSTEM ECLIPSE: All model engine tiers are down!")
        raise HTTPException(
            status_code=503, 
            detail={
                "error": "Service Unavailable", 
                "message": "All upstream LLM engine tiers are currently failing or rate-limited. Please retry later."
            }
        )
        
    # Validation catch for Gemini deployment credentials
    if provider == "gemini" and not GEMINI_KEY:
        logger.warning(f"⚠️ Gemini request skipped: Missing GEMINI_API_KEY. Forcing immediate fallback hop.")
        fallback_key = get_fallback_key(current_key)
        GATEWAY_FAILOVER_HOPS.labels(initial_key=current_key, fallback_key=fallback_key).inc()
        cfg = config_data[fallback_key]
        return await send_request(prompt, cfg["provider"], cfg["model_id"], cfg["cost_per_input_token"], cfg["cost_per_output_token"], fallback_key, config_data, failover_hops + 1)
    
    # 2. Circuit Breaker Execution Gatekeeper
    failure_count_key = f"circuit:{current_key}:failures"
    state_key = f"circuit:{current_key}:state"
    
    try:
        fail_count = await limiter.redis.get(failure_count_key)
        if fail_count and int(fail_count) >= 5:
            # If failures hit the threshold, read state to ensure we align the metrics
            current_state = await limiter.redis.get(state_key)
            if current_state != "open":
                await limiter.redis.set(state_key, "open")
                # Fixes Coverage Gap Advisory A2: Increments metric when circuit state opens
                GATEWAY_CIRCUIT_TRIPS.labels(provider_key=current_key).inc()
                
            fallback_key = get_fallback_key(current_key)
            logger.warning(f"🚨 CIRCUIT OPEN FOR '{current_key}'. Intercepting and rerouting traffic to fallback cluster '{fallback_key}'.")
            GATEWAY_FAILOVER_HOPS.labels(initial_key=current_key, fallback_key=fallback_key).inc()
            
            cfg = config_data[fallback_key]
            return await send_request(prompt, cfg["provider"], cfg["model_id"], cfg["cost_per_input_token"], cfg["cost_per_output_token"], fallback_key, config_data, failover_hops + 1)
    except HTTPException as http_err: 
        raise http_err
    except Exception as re: 
        logger.error(f"Circuit Breaker Lookup Guard Degraded: {str(re)}")

    # 3. Downstream Execution Engine Interaction
    output_text, p_tokens, c_tokens = "", 0, 0
    try:
        if provider == "ollama":
            # Direct Ollama requests out of the container to your local Windows host machine port
            target_host = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
            
            # Initialize a thread-safe custom async client container layout configuration
            client = ollama.AsyncClient(host=target_host)
            res = await client.chat(
                model=model_id, 
                messages=[{'role': 'user', 'content': prompt}]
            )
            output_text = res['message']['content']
            p_tokens = res.get('prompt_eval_count', len(prompt) // 4)
            c_tokens = res.get('eval_count', len(output_text) // 4)
            
        elif provider == "gemini":
            # Offload synchronous cloud client SDK loops to separate, thread-isolated async workers
            model = genai.GenerativeModel(model_id)
            res = await asyncio.to_thread(model.generate_content, prompt)
            output_text = res.text
            p_tokens = len(prompt) // 4
            c_tokens = len(output_text) // 4
            
        # Clear failures and close circuit seamlessly upon any successful execution run
        try:
            await limiter.redis.delete(failure_count_key)
            await limiter.redis.set(state_key, "closed")
        except Exception: 
            pass
            
    except Exception as e:
        logger.error(f"❌ Execution Failure encountered on tier node '{current_key}': {str(e)}")
        
        # Increment failure ledger atomic states inside Redis
        try:
            async with limiter.redis.pipeline(transaction=True) as pipe:
                pipe.incr(failure_count_key)
                pipe.expire(failure_count_key, 60) # Cooldown window reset time
                results = await pipe.execute()
            
            current_fails = results[0] if results else 0
            if current_fails and int(current_fails) >= 5:
                await limiter.redis.set(state_key, "open")
                logger.error(f"💥 FORCED TRANSACTION CIRCUIT TRIP TRIGGERED FOR: '{current_key}'")
                GATEWAY_CIRCUIT_TRIPS.labels(provider_key=current_key).inc()
        except Exception as pe: 
            logger.error(f"Failed to increment tracking failure counter states: {str(pe)}")
            
        # Silently deploy next available resilience tier to fulfill the prompt transaction
        fallback_key = get_fallback_key(current_key)
        GATEWAY_FAILOVER_HOPS.labels(initial_key=current_key, fallback_key=fallback_key).inc()
        cfg = config_data[fallback_key]
        return await send_request(prompt, cfg["provider"], cfg["model_id"], cfg["cost_per_input_token"], cfg["cost_per_output_token"], fallback_key, config_data, failover_hops + 1)
            
    # Calculate execution statistics 
    latency_ms = (time.time() - start_time) * 1000
    calculated_cost = (p_tokens * cost_per_input) + (c_tokens * cost_per_output)
    
    return StandardResponse(
        output_text=output_text,
        prompt_tokens=p_tokens,
        completion_tokens=c_tokens,
        total_tokens=p_tokens + c_tokens,
        latency_ms=latency_ms,
        cost_usd=calculated_cost,
        model_used=model_id
    )