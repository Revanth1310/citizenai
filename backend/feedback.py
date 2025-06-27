# feedback_db.py
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "feedbacks.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            message TEXT,
            sentiment TEXT,
            submitted_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_feedback(category, message, sentiment):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO feedbacks (category, message, sentiment, submitted_at) VALUES (?, ?, ?, datetime('now'))",
              (category, message, sentiment))
    conn.commit()
    conn.close()

def get_all_feedback():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM feedbacks ORDER BY submitted_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_sentiment_summary():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    result = {}
    for sentiment in ["positive", "neutral", "negative"]:
        cursor.execute("SELECT COUNT(*) FROM feedbacks WHERE sentiment=?", (sentiment,))
        result[sentiment] = cursor.fetchone()[0]
    conn.close()
    return result

def get_monthly_feedback_counts():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT strftime('%Y-%m', submitted_at) AS month, COUNT(*) 
        FROM feedbacks 
        GROUP BY month 
        ORDER BY month
    """)
    data = dict(cursor.fetchall())
    conn.close()
    return data
