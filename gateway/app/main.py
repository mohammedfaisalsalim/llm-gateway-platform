from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import asyncio

# Automatically load a local .env file on startup
load_dotenv()

from app.routes import chat
from app.database import init_db, bootstrap_budget_cache
from app.rate_limiter import limiter
from app.health import health_check_loop  # ← Add this import

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP SEQUENCING ---
    init_db()
    await bootstrap_budget_cache(limiter.redis)
    
    # Fire up the background circuit health checker task
    app.state.background_health_task = asyncio.create_task(health_check_loop())
    yield
    
    # --- SHUTDOWN SEQUENCING ---
    # Cancel background workers to prevent hanging processes
    app.state.background_health_task.cancel()
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