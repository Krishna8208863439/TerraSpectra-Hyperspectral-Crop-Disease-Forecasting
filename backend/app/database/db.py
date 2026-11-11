import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "terraspectra.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Datasets table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS datasets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        format TEXT NOT NULL,
        file_path TEXT NOT NULL,
        height INTEGER,
        width INTEGER,
        bands INTEGER,
        created_at TEXT NOT NULL,
        metadata_json TEXT
    )
    """)

    # Observations & Predictions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dataset_name TEXT NOT NULL,
        crop_type TEXT NOT NULL,
        condition TEXT NOT NULL,
        confidence REAL NOT NULL,
        is_healthy INTEGER NOT NULL,
        severity TEXT,
        stress_score REAL,
        indices_json TEXT,
        xai_summary TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # Forecasting records
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS forecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        analysis_id INTEGER,
        crop_type TEXT,
        peak_risk_day INTEGER,
        peak_risk_date TEXT,
        peak_risk_level TEXT,
        mean_projected_risk REAL,
        trajectory_json TEXT,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

def save_analysis(
    dataset_name: str,
    crop_type: str,
    condition: str,
    confidence: float,
    is_healthy: bool,
    severity: str,
    stress_score: float,
    indices: Dict[str, Any],
    xai_summary: str
) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO analyses (dataset_name, crop_type, condition, confidence, is_healthy, severity, stress_score, indices_json, xai_summary, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (dataset_name, crop_type, condition, confidence, 1 if is_healthy else 0, severity, stress_score, json.dumps(indices), xai_summary, now_str))
    rec_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return rec_id

def get_recent_analyses(limit: int = 15) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM analyses ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    results = [dict(r) for r in rows]
    conn.close()
    return results

def get_research_statistics() -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM analyses")
    total_scans = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM analyses WHERE is_healthy = 1")
    healthy_count = cursor.fetchone()[0]

    cursor.execute("SELECT condition, COUNT(*) as c FROM analyses GROUP BY condition ORDER BY c DESC")
    condition_counts = cursor.fetchall()

    conn.close()

    return {
        "total_spectral_analyses": total_scans,
        "healthy_count": healthy_count,
        "diseased_count": total_scans - healthy_count,
        "breakdown": [{"condition": row[0], "count": row[1]} for row in condition_counts]
    }

# Initialize schema on load
init_db()

