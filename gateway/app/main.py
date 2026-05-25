from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Automatically load a local .env file on startup
load_dotenv()

from app.routes import chat
from app.database import init_db
from app.rate_limiter import limiter

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on application startup
    init_db()
    yield
    # Runs on application shutdown (Prevents production connection leaks)
    await limiter.redis.aclose()

app = FastAPI(
    title="LLM Gateway", 
    version="1.0.0",
    lifespan=lifespan
)

# Register routes
app.include_router(chat.router, prefix="/v1")

@app.get("/health")
async def health(): 
    return {"status": "healthy"}