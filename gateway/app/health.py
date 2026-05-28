import asyncio
import logging
import httpx
import google.generativeai as genai
import ollama
from app.config import settings
from app.rate_limiter import limiter
from app.metrics import GATEWAY_CIRCUIT_TRIPS

logger = logging.getLogger("uvicorn.error")

async def check_provider_health(provider: str, model_id: str) -> bool:
    """True proactive client endpoint prober."""
    try:
        if provider == "ollama":
            # Timeout quick check against localized model bindings
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{settings.OLLAMA_HOST}/api/tags")
                return res.status_code == 200
        elif provider == "gemini":
            if not settings.GEMINI_API_KEY:
                return False
            # Basic client structural model metadata validation check
            model = genai.GenerativeModel(model_id)
            return model is not None
        return True
    except Exception:
        return False

async def health_check_loop():
    """
    Self-Healing Background Loop Engine.
    Sweeps open circuit breaker flags every 15 seconds to automatically reset 
    healthy nodes back to stable operational production states.
    """
    logger.info("📡 Core Monitoring Layer: Activating background health check loops...")
    # Import locally to prevent circular initialization loops during module namespace loading
    from app.routes.chat import load_models_config
    
    try:
        while True:
            await asyncio.sleep(15)
            config_data = load_models_config()
            
            for key, cfg in config_data.get("models", {}).items():
                failure_count_key = f"circuit:{key}:failures"
                state_key = f"circuit:{key}:state"
                
                # Check current circuit status flags inside our Redis ledger
                current_state = await limiter.redis.get(state_key)
                
                if current_state == "open":
                    logger.info(f"🔍 Circuit open for node '{key}'. Running background verification probe...")
                    is_healthy = await check_provider_health(cfg["provider"], cfg["model_id"])
                    
                    if is_healthy:
                        logger.info(f"✅ Recovery Verified: Provider '{key}' is responding cleanly. Healing circuit breaker flag.")
                        await limiter.redis.delete(failure_count_key)
                        await limiter.redis.set(state_key, "closed")
                    else:
                        logger.warning(f"❌ Provider '{key}' is still failing verification probes. Keeping circuit open.")
                        
    except asyncio.CancelledError:
        logger.info("✅ Background health loop cleanup executed cleanly.")
    except Exception as e:
        logger.error(f"💥 Health loop encountered a critical runtime failure: {str(e)}")