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