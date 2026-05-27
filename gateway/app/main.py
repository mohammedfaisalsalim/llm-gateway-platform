import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from prometheus_fastapi_instrumentator import Instrumentator

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
    #app.state.background_health_task = asyncio.create_task(health_check_loop())
    yield
    
    # --- SHUTDOWN SEQUENCING ---
    task = app.state.background_health_task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
        
    await limiter.redis.aclose()

app = FastAPI(
    title="LLM Gateway", 
    version="1.0.0",
    lifespan=lifespan
)

# Expose standard and system metrics monitoring schemas
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.include_router(chat.router, prefix="/v1")

@app.get("/health")
async def health(): 
    return {"status": "healthy"}