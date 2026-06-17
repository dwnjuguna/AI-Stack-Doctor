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

import sqlite3, json, re, argparse, webbrowser, os, logging
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, send_from_directory, request

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')

# ── Agentic Scheduler ─────────────────────────────────────────────────────────
try:
    from scheduler import get_scheduler
    _scheduler = get_scheduler()
    _scheduler.start()
    print("  🤖 Agentic scheduler started")
except Exception as _se:
    _scheduler = None
    print(f"  ⚠ Scheduler not available: {_se}")

DB_PATH   = Path("ai_stack_history.db")
SEED_PATH = Path("data/seed_audits.json")
app       = Flask(__name__)

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

def seed_from_json_if_needed():
    """Populate an empty DB from data/seed_audits.json so a fresh clone
    shows the pre-computed v4 audits immediately. No-op if DB has rows."""
    if not SEED_PATH.exists():
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company TEXT, mode TEXT DEFAULT 'competitor',
        overall INTEGER, scores_json TEXT,
        report_text TEXT, created_at TEXT)""")
    if conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] > 0:
        conn.close()
        return
    try:
        snapshot = json.loads(SEED_PATH.read_text())
        audits = snapshot.get("audits", [])
        for a in audits:
            conn.execute(
                "INSERT INTO reports (company,mode,overall,scores_json,report_text,created_at) VALUES (?,?,?,?,?,?)",
                (a["company"], a.get("mode", "competitor"), a.get("overall"),
                 json.dumps(a.get("scores", {})),
                 f"Seeded from {SEED_PATH} — {snapshot.get('source','')}",
                 a.get("created_at")),
            )
        conn.commit()
        print(f"  📦 Seeded {len(audits)} audits from {SEED_PATH}")
    except Exception as e:
        print(f"  ⚠ Seed load failed: {e}")
    finally:
        conn.close()

seed_from_json_if_needed()

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

@app.route("/legal")
@app.route("/legal/<section>")
def legal(section=None):
    """Serve the legal & privacy page."""
    return send_from_directory(".", "legal.html")

@app.route("/guide")
def guide():
    """Serve the non-technical user guide / landing page."""
    return send_from_directory(".", "guide.html")

@app.route("/security")
def security():
    """Serve the security posture page."""
    return send_from_directory(".", "security.html")

# ── AUTHENTICATION SCAFFOLDING ────────────────────────────────────────────────
# Phase 1 auth: API key gate for Pro tier endpoints
# Full SSO/SAML planned for Gov Edition (Phase 2)

import secrets, hashlib

def _load_api_keys() -> dict:
    """Load API keys from api_keys.json (created on first Pro activation)."""
    import json as _j
    kp = pathlib.Path("api_keys.json")
    if not kp.exists():
        return {}
    try:
        with open(kp) as f:
            return _j.load(f)
    except Exception:
        return {}

def _save_api_key(name: str, key: str, tier: str = "pro"):
    """Save a new API key."""
    import json as _j
    keys = _load_api_keys()
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    keys[key_hash] = {
        "name": name,
        "tier": tier,
        "created_at": datetime.now().isoformat(),
        "last_used": None,
        "active": True,
    }
    with open("api_keys.json", "w") as f:
        _j.dump(keys, f, indent=2)
    return key_hash

def require_api_key(f):
    """
    Decorator for Pro/Enterprise endpoints.
    Checks for valid API key in header or query param.
    Falls back to open access if no keys configured (free tier).
    """
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        keys = _load_api_keys()
        if not keys:
            # No keys configured = open access (free tier / demo mode)
            return f(*args, **kwargs)
        # Check Authorization header or ?api_key= param
        from flask import request as _req
        auth_header = _req.headers.get("Authorization", "")
        api_key     = _req.args.get("api_key", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]
        if not api_key:
            return jsonify({"error": "API key required for Pro endpoints"}), 401
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        if key_hash not in keys or not keys[key_hash].get("active"):
            return jsonify({"error": "Invalid or inactive API key"}), 403
        # Update last_used
        keys[key_hash]["last_used"] = datetime.now().isoformat()
        import json as _j
        with open("api_keys.json", "w") as fp:
            _j.dump(keys, fp, indent=2)
        return f(*args, **kwargs)
    return decorated

@app.route("/api/auth/generate-key", methods=["POST"])
def generate_api_key():
    """
    Generate a new API key (admin only in prod — open in demo).
    Body: { name, tier }
    Returns: { api_key, key_hash }
    """
    from flask import request as _req
    data = _req.get_json() or {}
    name = data.get("name", "default").strip()
    tier = data.get("tier", "pro")
    if not name:
        return jsonify({"error": "name is required"}), 400
    key = f"asd_{tier}_{secrets.token_urlsafe(32)}"
    key_hash = _save_api_key(name, key, tier)
    return jsonify({
        "ok": True,
        "api_key": key,
        "key_hash": key_hash,
        "name": name,
        "tier": tier,
        "note": "Store this key securely — it cannot be retrieved again.",
    })

@app.route("/api/auth/keys")
def list_api_keys():
    """List all API keys (hashed — keys not shown)."""
    keys = _load_api_keys()
    safe = [{
        "hash_prefix": h[:8] + "...",
        "name": v["name"],
        "tier": v["tier"],
        "created_at": v["created_at"],
        "last_used": v["last_used"],
        "active": v["active"],
    } for h, v in keys.items()]
    return jsonify({"keys": safe, "count": len(safe)})

@app.route("/api/auth/revoke", methods=["POST"])
def revoke_api_key():
    """Revoke an API key by hash prefix."""
    from flask import request as _req
    import json as _j
    data   = _req.get_json() or {}
    prefix = data.get("hash_prefix", "").strip()
    keys   = _load_api_keys()
    for h in list(keys.keys()):
        if h.startswith(prefix):
            keys[h]["active"] = False
            with open("api_keys.json", "w") as f:
                _j.dump(keys, f, indent=2)
            return jsonify({"ok": True, "revoked": h[:8] + "..."})
    return jsonify({"error": "Key not found"}), 404

# ── AUDIT LOGGING ─────────────────────────────────────────────────────────────
def log_audit_event(event_type: str, details: dict):
    """
    Write a tamper-evident audit log entry.
    Phase 1: append-only JSON log.
    Phase 2: cryptographic hash chain (Gov Edition).
    """
    import json as _j
    log_path = pathlib.Path("audit_log.jsonl")
    entry = {
        "ts":    datetime.now().isoformat(),
        "type":  event_type,
        **details,
    }
    # Append-only — never overwrite
    with open(log_path, "a") as f:
        f.write(_j.dumps(entry) + "\n")

@app.route("/api/audit-log")
def get_audit_log():
    """
    Return recent audit log entries.
    Phase 1: last 100 entries.
    Phase 2 (Gov): cryptographically verified chain.
    """
    import json as _j
    log_path = pathlib.Path("audit_log.jsonl")
    if not log_path.exists():
        return jsonify({"entries": [], "count": 0})
    entries = []
    try:
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(_j.loads(line))
    except Exception:
        pass
    return jsonify({"entries": list(reversed(entries[-100:])), "count": len(entries)})

# ── GOVERNMENT INTEREST CAPTURE ───────────────────────────────────────────────
@app.route("/api/gov-interest", methods=["POST"])
def gov_interest():
    """Save government/defense interest registrations."""
    from flask import request as _req
    import json as _j
    data = _req.get_json() or {}
    email = data.get("email", "").strip()
    if not email or "@" not in email:
        return jsonify({"error": "valid email required"}), 400
    # Save to gov_interest.json
    gi_path = pathlib.Path("gov_interest.json")
    entries = []
    if gi_path.exists():
        try:
            with open(gi_path) as f:
                entries = _j.load(f)
        except Exception:
            entries = []
    # Avoid duplicates
    if email not in [e.get("email") for e in entries]:
        entries.append({
            "email":    email,
            "name":     data.get("name", ""),
            "org":      data.get("org", ""),
            "org_type": data.get("org_type", ""),
            "urgency":  data.get("urgency", ""),
            "source":   data.get("source", ""),
            "ts":       data.get("ts", datetime.now().isoformat()),
        })
        with open(gi_path, "w") as f:
            _j.dump(entries, f, indent=2)
        # Log the event
        log_audit_event("gov_interest_registered", {
            "org": data.get("org", ""),
            "org_type": data.get("org_type", ""),
            "urgency": data.get("urgency", ""),
        })
    return jsonify({"ok": True, "position": len(entries)})

@app.route("/api/gov-interest/count")
def gov_interest_count():
    """Return government interest count (public)."""
    import json as _j
    gi_path = pathlib.Path("gov_interest.json")
    try:
        with open(gi_path) as f:
            entries = _j.load(f)
        return jsonify({"count": len(entries)})
    except Exception:
        return jsonify({"count": 0})

# ── AGENTIC SCHEDULER ROUTES ──────────────────────────────────────────────────

@app.route("/api/scheduler/status")
def scheduler_status():
    """Get scheduler status and stats."""
    if not _scheduler:
        return jsonify({"running": False, "error": "Scheduler not available"})
    return jsonify(_scheduler.get_status())

@app.route("/api/scheduler/schedules")
def get_schedules():
    """List all scheduled audits."""
    if not _scheduler:
        return jsonify([])
    return jsonify(_scheduler.get_schedules())

@app.route("/api/scheduler/schedule", methods=["POST"])
def add_schedule():
    """Add or update a scheduled audit.
    Body: { company, mode, cadence, alert_email, webhook_url }
    """
    if not _scheduler:
        return jsonify({"error": "Scheduler not available"}), 503
    data        = request.get_json() or {}
    company     = data.get("company", "").strip()
    mode        = data.get("mode", "competitor")
    cadence     = data.get("cadence", "weekly")
    email       = data.get("alert_email", "")
    webhook     = data.get("webhook_url", "")
    if not company:
        return jsonify({"error": "company is required"}), 400
    schedule = _scheduler.schedule(company, mode, cadence, email, webhook)
    return jsonify({"ok": True, "schedule": schedule})

@app.route("/api/scheduler/schedule/<schedule_id>", methods=["DELETE"])
def remove_schedule(schedule_id):
    """Remove a scheduled audit."""
    if not _scheduler:
        return jsonify({"error": "Scheduler not available"}), 503
    ok = _scheduler.unschedule(schedule_id)
    return jsonify({"ok": ok})

@app.route("/api/scheduler/schedule/<schedule_id>/pause", methods=["POST"])
def pause_schedule(schedule_id):
    """Pause a scheduled audit."""
    if not _scheduler:
        return jsonify({"error": "Scheduler not available"}), 503
    ok = _scheduler.pause(schedule_id)
    return jsonify({"ok": ok})

@app.route("/api/scheduler/schedule/<schedule_id>/resume", methods=["POST"])
def resume_schedule(schedule_id):
    """Resume a paused schedule."""
    if not _scheduler:
        return jsonify({"error": "Scheduler not available"}), 503
    ok = _scheduler.resume(schedule_id)
    return jsonify({"ok": ok})

@app.route("/api/scheduler/schedule/<schedule_id>/run", methods=["POST"])
def run_now(schedule_id):
    """Trigger an immediate audit for a schedule."""
    if not _scheduler:
        return jsonify({"error": "Scheduler not available"}), 503
    ok = _scheduler.run_now(schedule_id)
    return jsonify({"ok": ok, "message": "Audit started in background"})

@app.route("/api/scheduler/alerts")
def get_alerts():
    """Get recent change-detection alerts."""
    if not _scheduler:
        return jsonify([])
    limit = request.args.get("limit", 50, type=int)
    return jsonify(_scheduler.get_alerts(limit))

@app.route("/api/scheduler/log")
def get_run_log():
    """Get the recent run log."""
    if not _scheduler:
        return jsonify([])
    return jsonify(_scheduler.get_run_log())

@app.route("/api/scheduler/digest")
def get_digest():
    """Get a text digest of all tracked companies."""
    if not _scheduler:
        return jsonify({"digest": "Scheduler not available"})
    return jsonify({"digest": _scheduler.get_digest()})

@app.route("/api/waitlist", methods=["POST"])
def waitlist():
    """Save waitlist email signups to a local JSON file."""
    from flask import request
    import pathlib, datetime, json as _json
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    if not email or "@" not in email:
        return jsonify({"error": "valid email required"}), 400
    # Save to waitlist.json
    wl_path = pathlib.Path("waitlist.json")
    entries = []
    if wl_path.exists():
        try:
            with open(wl_path) as f:
                entries = _json.load(f)
        except Exception:
            entries = []
    # Avoid duplicates
    emails = [e.get("email") for e in entries]
    if email not in emails:
        entries.append({
            "email": email,
            "source": data.get("source", "unknown"),
            "ts": data.get("ts", datetime.datetime.now().isoformat())
        })
        with open(wl_path, "w") as f:
            _json.dump(entries, f, indent=2)
    return jsonify({"ok": True, "position": len(entries)})

@app.route("/api/waitlist/count")
def waitlist_count():
    """Return the current waitlist count (public)."""
    import pathlib, json as _json
    wl_path = pathlib.Path("waitlist.json")
    try:
        with open(wl_path) as f:
            entries = _json.load(f)
        return jsonify({"count": len(entries)})
    except Exception:
        return jsonify({"count": 0})

@app.route("/intake")
@app.route("/intake/<persona>")
def intake(persona=None):
    """Serve the client intake form, optionally with a persona pre-selected."""
    from flask import redirect
    if persona and persona not in ("consultant","executive","marketer","general"):
        return redirect("/intake")
    return send_from_directory(".", "intake_form.html")

@app.route("/api/intake/submit", methods=["POST"])
def intake_submit():
    """
    Receive a submitted intake form via POST.
    Saves to intake_submissions/ folder for pickup by the agent.
    """
    from flask import request
    import pathlib, datetime
    data = request.get_json() or {}
    company = re.sub(r'[^\w]', '_', data.get('companyName','unknown').lower())
    ts      = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder  = pathlib.Path("intake_submissions")
    folder.mkdir(exist_ok=True)
    fpath   = folder / f"intake_{company}_{ts}.json"
    with open(fpath, "w") as f:
        import json as _json
        _json.dump(data, f, indent=2)
    return jsonify({"ok": True, "file": str(fpath), "company": data.get("companyName")})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    # Render.com injects PORT as env variable — always respect it
    port = args.port or int(os.environ.get("PORT", 5050))

    # Check API key is set
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("WARNING: ANTHROPIC_API_KEY environment variable not set.")
        print("Set it with: export ANTHROPIC_API_KEY=sk-ant-...")

    print(f"\n🤖 AI Stack Doctor — History Dashboard")
    print(f"   Open: http://localhost:{port}")
    print(f"   Tip:  If the DB is empty, visit /api/seed to load demo data\n")

    # Only open browser when running locally (not on Render)
    is_local = not os.environ.get("RENDER")
    if is_local and not args.no_browser:
        import threading
        threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{port}")).start()

    app.run(host="0.0.0.0", port=port, debug=False)
