import sqlite3
import os
import logging

DB_PATH = "/app/gateway_metrics.db"
logger = logging.getLogger("uvicorn.error")

def init_db():
    """Initializes the database structure using context managers to prevent socket leaking."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id TEXT,
                model_used TEXT,
                latency_ms REAL,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                cost_usd REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    logger.info("¼ SQLite metric transaction tables verified operational.")

def log_request_to_db(team_id, model_used, latency_ms, prompt_tokens, completion_tokens, total_tokens, cost_usd):
    """Commits raw request execution logs to the disk layout securely via bounded scopes."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO request_logs 
                (team_id, model_used, latency_ms, prompt_tokens, completion_tokens, total_tokens, cost_usd)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (team_id, model_used, latency_ms, prompt_tokens, completion_tokens, total_tokens, cost_usd))
            conn.commit()
    except Exception as e:
        logger.error(f"❌ Metrics transaction failed database persistence write: {str(e)}")

async def bootstrap_budget_cache(redis_client):
    """
    Pre-warms multi-tenant balance allocations out of transaction logs into Redis memory caches.
    Guarantees initialization completion before the event loop handles any incoming requests.
    """
    try:
        if not os.path.exists(DB_PATH):
            return
            
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Calculate today's accumulated spending totals per team
            cursor.execute("""
                SELECT team_id, SUM(cost_usd) FROM request_logs 
                WHERE timestamp >= date('now') GROUP BY team_id
            """)
            rows = cursor.fetchall()
            
            for team_id, daily_cost in rows:
                if daily_cost:
                    budget_key = f"budget:{team_id}:daily_usd"
                    logger.info(f"💰 Seeding budget cache entry: Team '{team_id}' -> Realized Cost Value: ${daily_cost:.6f}")
                    
                    # Await the set operation natively with nx=True to ensure safe write concurrency
                    await redis_client.set(budget_key, float(daily_cost), nx=True)
                    
    except Exception as e:
        logger.error(f"⚠️ Failed to safely bootstrap tracking memory cache states: {str(e)}")