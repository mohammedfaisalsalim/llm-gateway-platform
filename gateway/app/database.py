import sqlite3
import os
import logging

DB_PATH = "/app/gateway_metrics.db"
logger = logging.getLogger("uvicorn.error")

def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    conn.close()
    logger.info("💾 SQLite metric transaction tables verified operational.")

def log_request_to_db(team_id, model_used, latency_ms, prompt_tokens, completion_tokens, total_tokens, cost_usd):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO request_logs 
            (team_id, model_used, latency_ms, prompt_tokens, completion_tokens, total_tokens, cost_usd)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (team_id, model_used, latency_ms, prompt_tokens, completion_tokens, total_tokens, cost_usd))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"❌ Metrics transaction failed database persistence write: {str(e)}")