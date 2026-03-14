"""SQLite database helpers for Climate Mesh."""

import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent / "climate_mesh.db"
_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Get a thread-local SQLite connection with WAL mode."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH), timeout=10)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA busy_timeout=5000")
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT NOT NULL,
            environment TEXT NOT NULL,
            temperature REAL,
            humidity REAL,
            air_quality REAL,
            water_level REAL,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS risk_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT NOT NULL,
            score REAL NOT NULL,
            level TEXT NOT NULL,
            temp_sub REAL,
            humidity_sub REAL,
            aqi_sub REAL,
            water_sub REAL,
            ai_multiplier REAL,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_readings_node ON sensor_readings(node_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_risk_node ON risk_scores(node_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_alerts_time ON alerts(timestamp);
    """)
    conn.commit()

    # Migration: add source column if not exists
    try:
        conn.execute("SELECT source FROM sensor_readings LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE sensor_readings ADD COLUMN source TEXT DEFAULT 'simulation'")
        conn.commit()


def insert_reading(node_id: str, environment: str, temperature: float,
                   humidity: float, air_quality: float, water_level: float,
                   source: str = "simulation"):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO sensor_readings (node_id, environment, temperature, humidity, air_quality, water_level, timestamp, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (node_id, environment, temperature, humidity, air_quality, water_level,
         datetime.now().isoformat(), source)
    )
    conn.commit()


def insert_risk_score(node_id: str, score: float, level: str,
                      temp_sub: float, humidity_sub: float, aqi_sub: float,
                      water_sub: float, ai_multiplier: float):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO risk_scores (node_id, score, level, temp_sub, humidity_sub, aqi_sub, water_sub, ai_multiplier, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (node_id, score, level, temp_sub, humidity_sub, aqi_sub, water_sub,
         ai_multiplier, datetime.now().isoformat())
    )
    conn.commit()


def insert_alert(node_id: str, alert_type: str, message: str, severity: str):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO alerts (node_id, alert_type, message, severity, timestamp) "
        "VALUES (?, ?, ?, ?, ?)",
        (node_id, alert_type, message, severity, datetime.now().isoformat())
    )
    conn.commit()


def get_latest_readings_per_node():
    """Get the most recent reading for each node."""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT s.* FROM sensor_readings s
        INNER JOIN (
            SELECT node_id, MAX(timestamp) as max_ts
            FROM sensor_readings GROUP BY node_id
        ) latest ON s.node_id = latest.node_id AND s.timestamp = latest.max_ts
        ORDER BY s.node_id
    """).fetchall()
    return [dict(r) for r in rows]


def get_risk_scores():
    """Get the most recent risk score for each node."""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT r.* FROM risk_scores r
        INNER JOIN (
            SELECT node_id, MAX(timestamp) as max_ts
            FROM risk_scores GROUP BY node_id
        ) latest ON r.node_id = latest.node_id AND r.timestamp = latest.max_ts
        ORDER BY r.score DESC
    """).fetchall()
    return [dict(r) for r in rows]


def get_alerts(limit: int = 50):
    """Get recent alerts."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_node_history(node_id: str, minutes: int = 10):
    """Get reading history for a specific node."""
    conn = _get_conn()
    cutoff = (datetime.now() - timedelta(minutes=minutes)).isoformat()
    rows = conn.execute(
        "SELECT * FROM sensor_readings WHERE node_id = ? AND timestamp > ? ORDER BY timestamp",
        (node_id, cutoff)
    ).fetchall()
    return [dict(r) for r in rows]


def clear_old_data(minutes: int = 30):
    """Remove data older than the specified minutes."""
    conn = _get_conn()
    cutoff = (datetime.now() - timedelta(minutes=minutes)).isoformat()
    conn.execute("DELETE FROM sensor_readings WHERE timestamp < ?", (cutoff,))
    conn.execute("DELETE FROM risk_scores WHERE timestamp < ?", (cutoff,))
    conn.execute("DELETE FROM alerts WHERE timestamp < ?", (cutoff,))
    conn.commit()
