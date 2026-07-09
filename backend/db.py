import sqlite3
import time
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "bandwidth_history.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS bandwidth_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            process_name TEXT NOT NULL,
            sent_bytes INTEGER NOT NULL,
            recv_bytes INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def log_snapshot(totals):
    """Write current per-process totals to the DB with a timestamp."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    ts = time.time()
    for name, v in totals.items():
        c.execute(
            "INSERT INTO bandwidth_log (timestamp, process_name, sent_bytes, recv_bytes) VALUES (?, ?, ?, ?)",
            (ts, name, v["sent"], v["recv"])
        )
    conn.commit()
    conn.close()

def get_history(process_name=None, since_seconds=3600):
    """Fetch historical records, optionally filtered by process name."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cutoff = time.time() - since_seconds
    if process_name:
        c.execute(
            "SELECT timestamp, process_name, sent_bytes, recv_bytes FROM bandwidth_log WHERE timestamp >= ? AND process_name = ? ORDER BY timestamp ASC",
            (cutoff, process_name)
        )
    else:
        c.execute(
            "SELECT timestamp, process_name, sent_bytes, recv_bytes FROM bandwidth_log WHERE timestamp >= ? ORDER BY timestamp ASC",
            (cutoff,)
        )
    rows = c.fetchall()
    conn.close()
    return [
        {"timestamp": r[0], "process_name": r[1], "sent_bytes": r[2], "recv_bytes": r[3]}
        for r in rows
    ]
