from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routes import chat
from app.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on application startup
    init_db()
    yield
    # Runs on application shutdown (clean up if needed)

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