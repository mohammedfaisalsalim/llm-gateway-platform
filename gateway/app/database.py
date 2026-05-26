import sqlite3
import asyncio
from datetime import datetime

DB_PATH = "gateway_metrics.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS request_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                timestamp TEXT, 
                prompt TEXT,
                model_used TEXT, 
                latency_ms REAL, 
                total_tokens INTEGER, 
                cost_usd REAL, 
                output_text TEXT
            )
        """)
        conn.commit()

def _sync_log_request(prompt, model, latency, tokens, cost, output):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO request_logs (timestamp, prompt, model_used, latency_ms, total_tokens, cost_usd, output_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (datetime.utcnow().isoformat(), prompt, model, latency, tokens, cost, output))
        conn.commit()

# Thread-isolated async wrapper to keep SQLite writes off the main event loop
async def log_request_to_db(prompt, model, latency, tokens, cost, output):
    await asyncio.to_thread(_sync_log_request, prompt, model, latency, tokens, cost, output)

def _sync_daily_balances_to_redis(redis_client):
    """
    Queries SQLite for all expenditures incurred today (UTC) 
    and returns a mapping of team_id -> total_cost.
    """
    from datetime import datetime
    import json
    
    # Extract today's date prefix (YYYY-MM-DD) matching our ISO timestamp schema
    today_prefix = datetime.utcnow().strftime("%Y-%m-%d")
    
    with sqlite3.connect(DB_PATH) as conn:
        # Note: Since your logs don't explicitly store team_id yet, we will aggregate 
        # based on the historical logs. For Day 10, we'll assume a structural query mapping.
        # Let's pull the columns to compute current values.
        cursor = conn.execute("""
            SELECT cost_usd FROM request_logs 
            WHERE timestamp LIKE ?
        """, (f"{today_prefix}%",))
        
        rows = cursor.fetchall()
        total_today = sum(row[0] for row in rows if row[0] is not None)
        return total_today

# This handles the raw computational aggregation off the main thread
async def bootstrap_budget_cache(redis_instance):
    """
    Asynchronous worker that pushes today's calculated spending from SQLite to Redis on startup.
    """
    # For day 10 initialization, we ensure the baseline total is cached
    total_spent = await asyncio.to_thread(_sync_daily_balances_to_redis, redis_instance)
    
    # Seed the default-team cache key in Redis
    # We will use the key space format: budget:spend:{team_id}
    await redis_instance.set("budget:spend:default-team", float(total_spent))
    await redis_instance.set("budget:spend:alpha-squad", float(total_spent)) # Seed our test team too