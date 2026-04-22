"""
AI Stack Doctor v3 — History Dashboard Server
==============================================
Serves the trend visualization dashboard, reading from ai_stack_history.db.

Usage:
    python3 dashboard_server.py              # runs on http://localhost:5050
    python3 dashboard_server.py --port 8000  # custom port

Requirements:
    pip3 install flask
"""

import sqlite3, json, re, argparse, webbrowser
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, send_from_directory

DB_PATH = Path("ai_stack_history.db")
app     = Flask(__name__)

CATEGORIES = [
    "GenAI / LLMs", "Agentic AI", "Machine Learning",
    "Data Engineering", "AI Platforms", "MLOps / LLMOps", "Cloud AI Services"
]

# ── DB helpers ────────────────────────────────────────────────────────────────
def db():
    if not DB_PATH.exists():
        return None
    return sqlite3.connect(DB_PATH)

def ensure_table():
    conn = db()
    if not conn: return
    conn.execute("""CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company TEXT, mode TEXT DEFAULT 'competitor',
        overall INTEGER, scores_json TEXT,
        report_text TEXT, created_at TEXT)""")
    conn.commit(); conn.close()

# ── API routes ────────────────────────────────────────────────────────────────
@app.route("/api/summary")
def summary():
    """Overview stats for the dashboard header."""
    ensure_table()
    conn = db()
    if not conn:
        return jsonify({"total":0,"companies":0,"avg_score":0,"latest":None})
    rows = conn.execute(
        "SELECT company, overall, created_at FROM reports ORDER BY id DESC"
    ).fetchall()
    conn.close()
    if not rows:
        return jsonify({"total":0,"companies":0,"avg_score":0,"latest":None})
    companies = list({r[0] for r in rows})
    scores    = [r[1] for r in rows if r[1]]
    return jsonify({
        "total":    len(rows),
        "companies": len(companies),
        "avg_score": round(sum(scores)/len(scores)) if scores else 0,
        "latest":    rows[0][2][:10] if rows else None,
    })

@app.route("/api/companies")
def companies():
    """Per-company latest scores + trend direction."""
    ensure_table()
    conn = db()
    if not conn: return jsonify([])
    rows = conn.execute(
        "SELECT company, overall, scores_json, mode, created_at FROM reports ORDER BY id DESC"
    ).fetchall()
    conn.close()

    seen, result = set(), []
    all_rows_by_company = {}
    for r in rows:
        co = r[0]
        if co not in all_rows_by_company:
            all_rows_by_company[co] = []
        all_rows_by_company[co].append({"overall": r[1], "date": r[4][:10]})

    for co, audits in all_rows_by_company.items():
        if co in seen: continue
        seen.add(co)
        latest = audits[0]
        prev   = audits[1] if len(audits) > 1 else None
        delta  = (latest["overall"] or 0) - (prev["overall"] or 0) if prev and prev["overall"] else 0
        # Parse scores from latest row
        scores_row = next((r for r in rows if r[0] == co), None)
        try:
            scores = json.loads(scores_row[2]) if scores_row and scores_row[2] else {}
        except: scores = {}
        result.append({
            "company":     co,
            "mode":        scores_row[3] if scores_row else "competitor",
            "overall":     latest["overall"],
            "delta":       delta,
            "audit_count": len(audits),
            "last_audit":  latest["date"],
            "scores":      scores,
        })
    result.sort(key=lambda x: x["overall"] or 0, reverse=True)
    return jsonify(result)

@app.route("/api/trend/<company>")
def trend(company):
    """Full audit history for a company — for trend chart."""
    ensure_table()
    conn = db()
    if not conn: return jsonify([])
    rows = conn.execute(
        "SELECT overall, scores_json, created_at, mode FROM reports WHERE company=? ORDER BY id ASC",
        (company.lower(),)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        try: scores = json.loads(r[1]) if r[1] else {}
        except: scores = {}
        result.append({
            "overall":    r[0],
            "scores":     scores,
            "date":       r[2][:10],
            "mode":       r[3],
        })
    return jsonify(result)

@app.route("/api/compare")
def compare():
    """Latest scores for all companies — for radar chart."""
    ensure_table()
    conn = db()
    if not conn: return jsonify([])
    # Get latest per company
    rows = conn.execute("""
        SELECT r.company, r.overall, r.scores_json FROM reports r
        INNER JOIN (SELECT company, MAX(id) as mid FROM reports GROUP BY company) m
        ON r.id = m.mid ORDER BY r.overall DESC LIMIT 8
    """).fetchall()
    conn.close()
    result = []
    for r in rows:
        try: scores = json.loads(r[2]) if r[2] else {}
        except: scores = {}
        result.append({"company": r[0], "overall": r[1], "scores": scores})
    return jsonify(result)

@app.route("/api/seed")
def seed():
    """Seed demo data if DB is empty — for first-run experience."""
    ensure_table()
    conn = db()
    count = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    if count > 0:
        conn.close()
        return jsonify({"seeded": False, "message": "Data already exists"})

    demo = [
        ("meta",      "competitor", 89, {"GenAI / LLMs":{"score":13,"total":14,"conf":"H"},"Agentic AI":{"score":10,"total":14,"conf":"M"},"Machine Learning":{"score":14,"total":14,"conf":"H"},"Data Engineering":{"score":13,"total":14,"conf":"H"},"AI Platforms":{"score":12,"total":14,"conf":"H"},"MLOps / LLMOps":{"score":11,"total":14,"conf":"H"},"Cloud AI Services":{"score":16,"total":16,"conf":"H"}}, "2025-10-15"),
        ("meta",      "competitor", 92, {"GenAI / LLMs":{"score":14,"total":14,"conf":"H"},"Agentic AI":{"score":12,"total":14,"conf":"H"},"Machine Learning":{"score":14,"total":14,"conf":"H"},"Data Engineering":{"score":13,"total":14,"conf":"H"},"AI Platforms":{"score":13,"total":14,"conf":"H"},"MLOps / LLMOps":{"score":12,"total":14,"conf":"H"},"Cloud AI Services":{"score":14,"total":16,"conf":"H"}}, "2026-01-12"),
        ("microsoft", "competitor", 91, {"GenAI / LLMs":{"score":13,"total":14,"conf":"H"},"Agentic AI":{"score":13,"total":14,"conf":"H"},"Machine Learning":{"score":12,"total":14,"conf":"H"},"Data Engineering":{"score":12,"total":14,"conf":"H"},"AI Platforms":{"score":13,"total":14,"conf":"H"},"MLOps / LLMOps":{"score":12,"total":14,"conf":"H"},"Cloud AI Services":{"score":16,"total":16,"conf":"H"}}, "2026-01-20"),
        ("google",    "competitor", 94, {"GenAI / LLMs":{"score":14,"total":14,"conf":"H"},"Agentic AI":{"score":12,"total":14,"conf":"H"},"Machine Learning":{"score":14,"total":14,"conf":"H"},"Data Engineering":{"score":13,"total":14,"conf":"H"},"AI Platforms":{"score":13,"total":14,"conf":"H"},"MLOps / LLMOps":{"score":13,"total":14,"conf":"H"},"Cloud AI Services":{"score":15,"total":16,"conf":"H"}}, "2026-02-03"),
        ("openai",    "competitor", 88, {"GenAI / LLMs":{"score":14,"total":14,"conf":"H"},"Agentic AI":{"score":13,"total":14,"conf":"H"},"Machine Learning":{"score":12,"total":14,"conf":"H"},"Data Engineering":{"score":10,"total":14,"conf":"M"},"AI Platforms":{"score":11,"total":14,"conf":"M"},"MLOps / LLMOps":{"score":13,"total":14,"conf":"H"},"Cloud AI Services":{"score":15,"total":16,"conf":"H"}}, "2026-02-10"),
        ("nvidia",    "competitor", 90, {"GenAI / LLMs":{"score":12,"total":14,"conf":"H"},"Agentic AI":{"score":9,"total":14,"conf":"M"},"Machine Learning":{"score":13,"total":14,"conf":"H"},"Data Engineering":{"score":11,"total":14,"conf":"H"},"AI Platforms":{"score":14,"total":14,"conf":"H"},"MLOps / LLMOps":{"score":13,"total":14,"conf":"H"},"Cloud AI Services":{"score":18,"total":16,"conf":"H"}}, "2026-02-18"),
        ("amazon",    "competitor", 87, {"GenAI / LLMs":{"score":11,"total":14,"conf":"H"},"Agentic AI":{"score":11,"total":14,"conf":"H"},"Machine Learning":{"score":12,"total":14,"conf":"H"},"Data Engineering":{"score":13,"total":14,"conf":"H"},"AI Platforms":{"score":12,"total":14,"conf":"H"},"MLOps / LLMOps":{"score":12,"total":14,"conf":"H"},"Cloud AI Services":{"score":16,"total":16,"conf":"H"}}, "2026-03-01"),
        ("apple",     "competitor", 79, {"GenAI / LLMs":{"score":10,"total":14,"conf":"M"},"Agentic AI":{"score":9,"total":14,"conf":"M"},"Machine Learning":{"score":12,"total":14,"conf":"H"},"Data Engineering":{"score":10,"total":14,"conf":"M"},"AI Platforms":{"score":11,"total":14,"conf":"H"},"MLOps / LLMOps":{"score":10,"total":14,"conf":"M"},"Cloud AI Services":{"score":17,"total":16,"conf":"H"}}, "2026-03-10"),
        ("salesforce","competitor", 76, {"GenAI / LLMs":{"score":11,"total":14,"conf":"H"},"Agentic AI":{"score":13,"total":14,"conf":"H"},"Machine Learning":{"score":10,"total":14,"conf":"M"},"Data Engineering":{"score":10,"total":14,"conf":"M"},"AI Platforms":{"score":11,"total":14,"conf":"H"},"MLOps / LLMOps":{"score":9,"total":14,"conf":"M"},"Cloud AI Services":{"score":12,"total":16,"conf":"M"}}, "2026-03-15"),
        ("tesla",     "competitor", 81, {"GenAI / LLMs":{"score":9,"total":14,"conf":"M"},"Agentic AI":{"score":10,"total":14,"conf":"M"},"Machine Learning":{"score":14,"total":14,"conf":"H"},"Data Engineering":{"score":13,"total":14,"conf":"H"},"AI Platforms":{"score":12,"total":14,"conf":"H"},"MLOps / LLMOps":{"score":11,"total":14,"conf":"H"},"Cloud AI Services":{"score":12,"total":16,"conf":"M"}}, "2026-03-22"),
        ("adobe",     "competitor", 73, {"GenAI / LLMs":{"score":12,"total":14,"conf":"H"},"Agentic AI":{"score":8,"total":14,"conf":"M"},"Machine Learning":{"score":10,"total":14,"conf":"M"},"Data Engineering":{"score":11,"total":14,"conf":"H"},"AI Platforms":{"score":10,"total":14,"conf":"M"},"MLOps / LLMOps":{"score":9,"total":14,"conf":"M"},"Cloud AI Services":{"score":13,"total":16,"conf":"H"}}, "2026-03-28"),
        ("netflix",   "competitor", 84, {"GenAI / LLMs":{"score":9,"total":14,"conf":"M"},"Agentic AI":{"score":8,"total":14,"conf":"L"},"Machine Learning":{"score":13,"total":14,"conf":"H"},"Data Engineering":{"score":14,"total":14,"conf":"H"},"AI Platforms":{"score":12,"total":14,"conf":"H"},"MLOps / LLMOps":{"score":13,"total":14,"conf":"H"},"Cloud AI Services":{"score":15,"total":16,"conf":"H"}}, "2026-04-01"),
        ("oracle",    "competitor", 68, {"GenAI / LLMs":{"score":9,"total":14,"conf":"M"},"Agentic AI":{"score":7,"total":14,"conf":"M"},"Machine Learning":{"score":9,"total":14,"conf":"M"},"Data Engineering":{"score":12,"total":14,"conf":"H"},"AI Platforms":{"score":10,"total":14,"conf":"M"},"MLOps / LLMOps":{"score":8,"total":14,"conf":"M"},"Cloud AI Services":{"score":13,"total":16,"conf":"H"}}, "2026-04-05"),
        ("amd",       "competitor", 71, {"GenAI / LLMs":{"score":7,"total":14,"conf":"M"},"Agentic AI":{"score":6,"total":14,"conf":"L"},"Machine Learning":{"score":10,"total":14,"conf":"H"},"Data Engineering":{"score":8,"total":14,"conf":"M"},"AI Platforms":{"score":13,"total":14,"conf":"H"},"MLOps / LLMOps":{"score":10,"total":14,"conf":"M"},"Cloud AI Services":{"score":17,"total":16,"conf":"H"}}, "2026-04-10"),
        ("broadcom",  "competitor", 65, {"GenAI / LLMs":{"score":7,"total":14,"conf":"M"},"Agentic AI":{"score":6,"total":14,"conf":"L"},"Machine Learning":{"score":9,"total":14,"conf":"M"},"Data Engineering":{"score":9,"total":14,"conf":"M"},"AI Platforms":{"score":12,"total":14,"conf":"H"},"MLOps / LLMOps":{"score":8,"total":14,"conf":"M"},"Cloud AI Services":{"score":14,"total":16,"conf":"H"}}, "2026-04-12"),
        ("intel",     "competitor", 63, {"GenAI / LLMs":{"score":7,"total":14,"conf":"M"},"Agentic AI":{"score":5,"total":14,"conf":"L"},"Machine Learning":{"score":9,"total":14,"conf":"M"},"Data Engineering":{"score":8,"total":14,"conf":"M"},"AI Platforms":{"score":12,"total":14,"conf":"H"},"MLOps / LLMOps":{"score":9,"total":14,"conf":"M"},"Cloud AI Services":{"score":13,"total":16,"conf":"H"}}, "2026-04-15"),
        ("mistral",   "competitor", 77, {"GenAI / LLMs":{"score":13,"total":14,"conf":"H"},"Agentic AI":{"score":10,"total":14,"conf":"M"},"Machine Learning":{"score":11,"total":14,"conf":"H"},"Data Engineering":{"score":7,"total":14,"conf":"M"},"AI Platforms":{"score":8,"total":14,"conf":"M"},"MLOps / LLMOps":{"score":11,"total":14,"conf":"H"},"Cloud AI Services":{"score":17,"total":16,"conf":"M"}}, "2026-04-18"),
        ("anthropic", "competitor", 85, {"GenAI / LLMs":{"score":14,"total":14,"conf":"H"},"Agentic AI":{"score":12,"total":14,"conf":"H"},"Machine Learning":{"score":12,"total":14,"conf":"H"},"Data Engineering":{"score":9,"total":14,"conf":"M"},"AI Platforms":{"score":10,"total":14,"conf":"M"},"MLOps / LLMOps":{"score":13,"total":14,"conf":"H"},"Cloud AI Services":{"score":15,"total":16,"conf":"H"}}, "2026-04-20"),
    ]

    for co, mode, overall, scores, date in demo:
        conn.execute(
            "INSERT INTO reports (company,mode,overall,scores_json,report_text,created_at) VALUES (?,?,?,?,?,?)",
            (co, mode, overall, json.dumps(scores), f"Demo report for {co}", date+"T12:00:00")
        )
    conn.commit(); conn.close()
    return jsonify({"seeded": True, "records": len(demo)})

@app.route("/")
def index():
    return send_from_directory(".", "dashboard.html")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5050)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    print(f"\n🤖 AI Stack Doctor — History Dashboard")
    print(f"   Open: http://localhost:{args.port}")
    print(f"   Tip:  If the DB is empty, visit /api/seed to load demo data\n")
    if not args.no_browser:
        import threading, time
        threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{args.port}")).start()
    app.run(host="0.0.0.0", port=args.port, debug=False)
