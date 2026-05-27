import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Automatically load local .env properties configurations
load_dotenv()

from app.routes import chat
from app.database import init_db, bootstrap_budget_cache
from app.rate_limiter import limiter
from app.health import health_check_loop  

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP SEQUENCING ---
    init_db()
    await bootstrap_budget_cache(limiter.redis)
    
    # Mount the proactive loop task onto the background worker allocations
    app.state.background_health_task = asyncio.create_task(health_check_loop())
    yield
    
    # --- SHUTDOWN SEQUENCING ---
    # FIX 4: Await the cancelled task tracking safely to prevent raw unhandled exception dump logs
    task = app.state.background_health_task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        # Expected behavior for clean worker shutdowns
        pass
        
    await limiter.redis.aclose()

app = FastAPI(
    title="LLM Gateway", 
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(chat.router, prefix="/v1")

@app.get("/health")
async def health(): 
    return {"status": "healthy"}