import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from app.health import health_check_loop
from prometheus_fastapi_instrumentator import Instrumentator

import os
import logging

# Ensure environment variables are loaded prior to downstream module imports
load_dotenv()

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.database import init_db
from app.classifier import bootstrap_classifier
from app.health import health_check_loop
from app.routes.chat import router

# Configure logging layout format
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Unified Application Lifespan State Manager.
    Handles sequential ecosystem startup dependencies and graceful background task teardown.
    """
    # --- STARTUP SEQUENCE ---
    logger.info("🚀 Bootstrapping LLM Gateway Core Components...")
    
    # 1. Initialize local SQLite tracking metrics database tables
    init_db()
    
    # 2. Warm up and load the Scikit-Learn text classification vectorizer pipelines
    bootstrap_classifier()
    
    # 3. Initialize and activate the proactive background circuit recovery task
    # Fixes Day 13 Blocker: Restores the background ping and health recovery system
    logger.info("⏱️ Activating proactive background health monitoring worker loops...")
    app.state.background_health_task = asyncio.create_task(health_check_loop())
    
    yield
    
    # --- SHUTDOWN SEQUENCE ---
    logger.info("🛑 Initiating graceful teardown sequences...")
    
    # Cancel the active background task smoothly without raising operational errors
    try:
        task = app.state.background_health_task
        task.cancel()
        await task
        logger.info("✅ Background health monitoring loops stopped cleanly.")
    except AttributeError:
        logger.warning("⚠️ Background health task pointer was not found during shutdown context.")
    except asyncio.CancelledError:
        logger.info("✅ Background health task tracking terminated smoothly.")
        
    logger.info("Platform offline.")

# Initialize the main ASGI framework wrapper
app = FastAPI(
    title="LLM Gateway Platform",
    description="Intelligent Machine Learning API Gateway featuring self-healing routing tier clusters.",
    version="1.0.0",
    lifespan=lifespan
)

# Attach production cross-origin resource sharing structural boundaries
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize and mount Prometheus endpoint instrumentation hooks
# Exposes the /metrics path on port 8000 for target scrapers
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Attach operational network routing endpoints
app.include_router(router)

@app.get("/")
async def root_ping():
    """
    Global cluster validation target path.
    """
    return {
        "status": "online",
        "service": "llm-gateway-core",
        "telemetry_state": "instrumented"
    }