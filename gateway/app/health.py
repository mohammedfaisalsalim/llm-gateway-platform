import asyncio
import logging
import ollama
import google.generativeai as genai
from app.rate_limiter import limiter

logger = logging.getLogger("uvicorn.error")

async def health_check_loop():
    """Background asynchronous worker pinging providers to heal open circuits."""
    await asyncio.sleep(5) # Gentle startup delay
    while True:
        logger.info("🔍 Background Circuit Breaker health checks running...")
        
        # Define lightweight test probes
        providers_to_test = {
            "llama3.2": {"provider": "ollama", "model": "llama3.2:3b"},
            "mistral": {"provider": "ollama", "model": "mistral:7b"},
            "gemini-flash": {"provider": "gemini", "model": "gemini-2.0-flash"}
        }

        for key, info in providers_to_test.items():
            state = await limiter.redis.get(f"circuit:{key}:state")
            # We only need to actively probe if the circuit is marked open (tripped)
            if state == "open":
                logger.info(f"Probing tripped provider '{key}' for signs of recovery...")
                success = False
                try:
                    if info["provider"] == "ollama":
                        await asyncio.to_thread(ollama.chat, model=info["model"], messages=[{'role': 'user', 'content': 'ping'}])
                        success = True
                    elif info["provider"] == "gemini":
                        model = genai.GenerativeModel(info["model"])
                        await asyncio.to_thread(model.generate_content, "ping")
                        success = True
                except Exception:
                    success = False

                if success:
                    logger.info(f"✅ Provider '{key}' has healed! Closing circuit.")
                    await limiter.redis.delete(f"circuit:{key}:failures")
                    await limiter.redis.set(f"circuit:{key}:state", "closed")
                else:
                    logger.warning(f"⚠️ Provider '{key}' is still unresponsive. Circuit stays open.")

        await asyncio.sleep(30)