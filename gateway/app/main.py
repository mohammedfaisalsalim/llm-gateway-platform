from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Automatically load a local .env file on startup
load_dotenv()

from app.routes import chat
from app.database import init_db, bootstrap_budget_cache
from app.rate_limiter import limiter

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP SEQUENCING ---
    # 1. Initialize SQLite transactional log schema if it doesn't exist
    init_db()
    
    # 2. Synchronize and seed the Redis fast-cache from today's historical logs
    await bootstrap_budget_cache(limiter.redis)
    yield
    
    # --- SHUTDOWN SEQUENCING ---
    # 3. Cleanly close the Redis connection pool to prevent socket leaks
    await limiter.redis.aclose()

app = FastAPI(
    title="LLM Gateway", 
    version="1.0.0",
    lifespan=lifespan
)

# Register API routes
app.include_router(chat.router, prefix="/v1")

@app.get("/health")
async def health(): 
    return {"status": "healthy"}