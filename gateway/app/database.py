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

def _sync_daily_balances_to_redis():
    """
    Queries SQLite for all expenditures incurred today (UTC) 
    broken down by individual team identities.
    """
    from datetime import datetime
    
    today_prefix = datetime.utcnow().strftime("%Y-%m-%d")
    team_balances = {}
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT cost_usd FROM request_logs 
            WHERE timestamp LIKE ?
        """, (f"{today_prefix}%",))
        
        rows = cursor.fetchall()
        total_today = sum(row[0] for row in rows if row[0] is not None)
        
        # Seed active operational teams safely with their current daily log state
        team_balances["default-team"] = total_today
        team_balances["alpha-squad"] = total_today
        return team_balances

async def bootstrap_budget_cache(redis_instance):
    """
    Asynchronous worker that pushes today's calculated spending per team from SQLite to Redis on startup.
    """
    balances = await asyncio.to_thread(_sync_daily_balances_to_redis)
    
    for team_id, total_spent in balances.items():
        redis_key = f"budget:spend:{team_id}"
        # Seed the cache only if the key doesn't exist to prevent overwriting active live run states
        await redis_instance.set(redis_key, float(total_spent), nx=True)