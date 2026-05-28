import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# FIX 2: Environment variables MUST be loaded before any internal app modules import
load_dotenv()

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.database import init_db
from app.classifier import bootstrap_classifier
from app.health import health_check_loop
from app.routes.chat import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Bootstrapping LLM Gateway Core Components...")
    init_db()
    bootstrap_classifier()
    
    logger.info("⏱️ Activating background monitoring loops...")
    app.state.background_health_task = asyncio.create_task(health_check_loop())
    yield
    
    logger.info("🛑 Initiating graceful teardown sequences...")
    # FIX 4: Use hasattr to completely eliminate AttributeError crashes on startup failures
    if hasattr(app.state, 'background_health_task'):
        task = app.state.background_health_task
        task.cancel()
        try:
            await task
            logger.info("✅ Background health monitoring loops stopped cleanly.")
        except asyncio.CancelledError:
            logger.info("✅ Background health task tracking terminated smoothly.")
    else:
        logger.warning("⚠️ Background health task was never initialized.")

app = FastAPI(
    title="LLM Gateway Platform",
    description="Intelligent Machine Learning API Gateway with self-healing routing tier clusters.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrument and expose Prometheus tracking metrics endpoints natively
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
app.include_router(router)

@app.get("/")
async def root_ping():
    return {
        "status": "online",
        "service": "llm-gateway-core",
        "telemetry_state": "instrumented"
    }