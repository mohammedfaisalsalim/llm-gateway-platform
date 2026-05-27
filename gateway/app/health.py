import asyncio
import logging
import ollama
import google.generativeai as genai
from app.rate_limiter import limiter

logger = logging.getLogger("uvicorn.error")

async def health_check_loop():
    """Background asynchronous worker proactively pinging all providers to maintain real-time health mappings."""
    await asyncio.sleep(5)  # Gentle startup delay
    while True:
        logger.info("🔍 Proactive Circuit Breaker health loop sweeping all engines...")
        
        providers_to_test = {
            "llama3.2": {"provider": "ollama", "model": "llama3.2:3b"},
            "mistral": {"provider": "ollama", "model": "mistral:7b"},
            "gemini-flash": {"provider": "gemini", "model": "gemini-2.0-flash"}
        }

        for key, info in providers_to_test.items():
            success = False
            try:
                if info["provider"] == "ollama":
                    await asyncio.to_thread(
                        ollama.chat, 
                        model=info["model"], 
                        messages=[{'role': 'user', 'content': 'ping'}]
                    )
                    success = True
                elif info["provider"] == "gemini":
                    # Check if key exists to prevent internal test validation crashes
                    from app.providers import GEMINI_KEY
                    if not GEMINI_KEY:
                        raise ValueError("No API Key configured")
                    model = genai.GenerativeModel(info["model"])
                    await asyncio.to_thread(model.generate_content, "ping")
                    success = True
            except Exception:
                success = False

            failure_count_key = f"circuit:{key}:failures"
            state_key = f"circuit:{key}:state"

            if success:
                current_state = await limiter.redis.get(state_key)
                if current_state == b"open" or current_state == "open":
                    logger.info(f"✅ Tripped provider '{key}' recovered! Closing circuit.")
                
                # Clear all failure tracks and mark closed safely
                await limiter.redis.delete(failure_count_key)
                await limiter.redis.set(state_key, "closed")
            else:
                # If it fails the health check probe, smoothly increment its tracking state
                logger.warning(f"⚠️ Proactive probe failed for provider '{key}'. Tracking failure increment.")
                async with limiter.redis.pipeline(transaction=True) as pipe:
                    pipe.incr(failure_count_key)
                    pipe.expire(failure_count_key, 60)
                    results = await pipe.execute()
                
                current_fails = results[0] if results else 0
                if current_fails and int(current_fails) >= 5:
                    await limiter.redis.set(state_key, "open")
                    logger.error(f"💥 PROACTIVE CIRCUIT TRIP: '{key}' forced OPEN by background pinger loop.")

        await asyncio.sleep(30)