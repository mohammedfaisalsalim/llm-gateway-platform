import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger("uvicorn.error")

DB_PATH = "gateway_metrics.db"

def init_db():
    """
    Initializes the local relational SQLite tracking metrics database tables.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_logs (
                id TEXT PRIMARY KEY,
                team_id TEXT NOT NULL,
                prompt TEXT,
                model_used TEXT,
                model_tier INTEGER,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                latency_ms REAL,
                cost_usd REAL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()
        logger.info("💾 SQLite local operational metrics tables initialized successfully.")
    except Exception as e:
        logger.critical(f"💥 Critical error initializing relational database tables: {str(e)}")
    finally:
        conn.close()

def log_request_to_db(
    request_id: str,
    team_id: str,
    prompt: str,
    model_used: str,
    model_tier: int,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    latency_ms: float,
    cost_usd: float
):
    """
    Persists an analytical request event log transaction record onto local disk.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO request_logs (
                id, team_id, prompt, model_used, model_tier, 
                prompt_tokens, completion_tokens, total_tokens, 
                latency_ms, cost_usd, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id, team_id, prompt[:500], model_used, model_tier,
            prompt_tokens, completion_tokens, total_tokens,
            latency_ms, cost_usd, datetime.utcnow().isoformat()
        ))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to commit metrics record into SQLite ledger row: {str(e)}")
    finally:
        conn.close()

def bootstrap_budget_cache():
    """
    Scans historical SQLite transaction records for the current calendar day to 
    dynamically reconstruct and seed individual live Redis multi-tenant budget ledger hashes.
    Fixes Day 13/14 Shared Budget Error: Filters properly using GROUP BY team_id.
    """
    import asyncio
    from app.rate_limiter import limiter  # Access the active Redis client wrapper connection
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Query isolates and sums total cost fields grouped exclusively by individual team tracking IDs
        cursor.execute("""
            SELECT team_id, SUM(cost_usd) 
            FROM request_logs 
            WHERE timestamp >= date('now', 'start of day')
            GROUP BY team_id
        """)
        records = cursor.fetchall()
        
        if not records:
            logger.info("ℹ️ No historical transactions found for today. Redis budget cache initialized clean.")
            return

        # Fetch the running event loop layout line to pipeline strings into Redis
        loop = asyncio.get_event_loop()
        
        for team_id, daily_spend in records:
            if team_id and daily_spend is not None:
                redis_key = f"circuit:{team_id}:budget_spent"
                
                # Execute the synchronous Redis command string thread-safely inside the async engine loop
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        limiter.redis.set(redis_key, str(daily_spend)), 
                        loop
                    )
                else:
                    # Fallback context safe run parameter logic sequence
                    import redis
                    r_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
                    r_client.set(redis_key, str(daily_spend))
                    
                logger.info(f"💾 Seeded multi-tenant budget tracker cache for team '{team_id}': ${daily_spend:.6f}")
                
    except sqlite3.OperationalError as e:
        logger.warning(f"Budget metrics cache sync skipped (Table may be empty or uninitialized): {str(e)}")
    except Exception as ex:
        logger.error(f"Error encountered during database cache bootstrapping: {str(ex)}")
    finally:
        conn.close()