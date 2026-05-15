"""
AI Stack Doctor v4 — Agentic Scheduler
=======================================
Fully autonomous audit scheduling, change detection,
competitive alerts, and digest reports.

Zero external dependencies — uses stdlib only:
  threading, sqlite3, time, json, smtplib, email

Features:
  - Scheduled audits (daily/weekly/monthly/quarterly)
  - Change detection — alerts when signals shift
  - Competitive intelligence alerts
  - Digest reports (email or webhook)
  - Full audit history with delta tracking
  - REST API for schedule management

Usage:
  from scheduler import AgenticScheduler
  scheduler = AgenticScheduler()
  scheduler.start()
"""

import sqlite3
import json
import threading
import time
import logging
import smtplib
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("asd.scheduler")

DB_PATH    = Path("ai_stack_history.db")
SCHED_PATH = Path("schedules.json")

# ── Cadence helpers ────────────────────────────────────────────────────────────
CADENCE_SECONDS = {
    "hourly":      3600,
    "daily":       86400,
    "weekly":      604800,
    "monthly":     2592000,   # 30 days
    "quarterly":   7776000,   # 90 days
}

CADENCE_LABELS = {
    "hourly":    "Every hour",
    "daily":     "Every day",
    "weekly":    "Every week",
    "monthly":   "Every month",
    "quarterly": "Every quarter",
}


# ══════════════════════════════════════════════════════════════════════════════
# ALERT ENGINE
# ══════════════════════════════════════════════════════════════════════════════
class AlertEngine:
    """
    Detects meaningful changes between audit runs and
    routes alerts to configured destinations.
    """

    SIGNIFICANCE_THRESHOLD = 3  # Score delta points to trigger alert

    def __init__(self):
        self.destinations = []  # List of alert destinations

    def add_email(self, address: str, smtp_config: dict):
        """Add an email alert destination."""
        self.destinations.append({
            "type": "email",
            "address": address,
            "smtp": smtp_config,
        })

    def add_webhook(self, url: str, headers: dict = None):
        """Add a webhook alert destination."""
        self.destinations.append({
            "type": "webhook",
            "url": url,
            "headers": headers or {},
        })

    def check_for_alerts(self, company: str, prev_score: int,
                         new_score: int, prev_scores: dict, new_scores: dict) -> list:
        """
        Compare previous and new audit results.
        Returns list of alert messages if significant changes detected.
        """
        alerts = []
        delta = new_score - prev_score

        # Overall score change
        if abs(delta) >= self.SIGNIFICANCE_THRESHOLD:
            direction = "improved" if delta > 0 else "declined"
            alerts.append({
                "type": "score_change",
                "severity": "high" if abs(delta) >= 8 else "medium",
                "company": company,
                "message": (
                    f"{company.title()} AI stack {direction} by {abs(delta)} points "
                    f"({prev_score} → {new_score}/100)"
                ),
                "delta": delta,
            })

        # Category-level changes
        for cat, new_s in new_scores.items():
            if cat not in prev_scores:
                continue
            old_s   = prev_scores[cat]
            cat_delta = new_s.get("score", 0) - old_s.get("score", 0)
            if abs(cat_delta) >= 2:
                direction = "▲" if cat_delta > 0 else "▼"
                alerts.append({
                    "type": "category_change",
                    "severity": "medium",
                    "company": company,
                    "category": cat,
                    "message": (
                        f"{company.title()} — {cat}: "
                        f"{direction} {abs(cat_delta)} points "
                        f"({old_s.get('score',0)}/{old_s.get('total',14)} → "
                        f"{new_s.get('score',0)}/{new_s.get('total',14)})"
                    ),
                    "delta": cat_delta,
                })

        return alerts

    def send_alert(self, alert: dict):
        """Route an alert to all configured destinations."""
        for dest in self.destinations:
            try:
                if dest["type"] == "email":
                    self._send_email(alert, dest)
                elif dest["type"] == "webhook":
                    self._send_webhook(alert, dest)
            except Exception as e:
                logger.error(f"Alert delivery failed ({dest['type']}): {e}")

    def _send_email(self, alert: dict, dest: dict):
        smtp = dest["smtp"]
        msg  = MIMEMultipart("alternative")
        msg["Subject"] = f"🤖 AI Stack Alert: {alert['company'].title()} — {alert['message'][:60]}"
        msg["From"]    = smtp.get("from", "alerts@ai-stack-doctor.com")
        msg["To"]      = dest["address"]

        body = f"""
AI STACK DOCTOR — AUTOMATED ALERT
{'='*50}

{alert['message']}

Type:     {alert['type'].replace('_', ' ').title()}
Severity: {alert['severity'].upper()}
Time:     {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}

View full dashboard: https://ai-stack-doctor.onrender.com

--
AI Stack Doctor Agentic Scheduler
Unsubscribe: reply with STOP
        """.strip()

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp.get("host", "smtp.gmail.com"),
                          smtp.get("port", 587)) as server:
            server.starttls()
            server.login(smtp["user"], smtp["password"])
            server.send_message(msg)

        logger.info(f"Email alert sent to {dest['address']}")

    def _send_webhook(self, alert: dict, dest: dict):
        payload = json.dumps({
            "source": "ai-stack-doctor",
            "alert": alert,
            "timestamp": datetime.now().isoformat(),
        }).encode()

        req = urllib.request.Request(
            dest["url"],
            data=payload,
            headers={
                "Content-Type": "application/json",
                **dest.get("headers", {}),
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            logger.info(f"Webhook delivered: {r.status} {dest['url']}")


# ══════════════════════════════════════════════════════════════════════════════
# SCHEDULE STORE
# ══════════════════════════════════════════════════════════════════════════════
class ScheduleStore:
    """
    Persists audit schedules to schedules.json.
    Each schedule has: company, mode, cadence, next_run, last_run, alert_config.
    """

    def __init__(self):
        self.path = SCHED_PATH
        self._lock = threading.Lock()

    def load(self) -> list:
        with self._lock:
            if not self.path.exists():
                return []
            try:
                with open(self.path) as f:
                    return json.load(f)
            except Exception:
                return []

    def save(self, schedules: list):
        with self._lock:
            with open(self.path, "w") as f:
                json.dump(schedules, f, indent=2)

    def add(self, company: str, mode: str, cadence: str,
            alert_email: str = "", webhook_url: str = "") -> dict:
        schedules = self.load()
        # Update existing or create new
        existing = next((s for s in schedules
                         if s["company"].lower() == company.lower()), None)
        now = datetime.now().isoformat()
        interval = CADENCE_SECONDS.get(cadence, 604800)
        next_run = (datetime.now() + timedelta(seconds=interval)).isoformat()

        if existing:
            existing.update({
                "cadence": cadence,
                "next_run": next_run,
                "alert_email": alert_email,
                "webhook_url": webhook_url,
                "updated_at": now,
            })
            schedule = existing
        else:
            schedule = {
                "id": f"sched_{int(time.time())}_{company.lower().replace(' ','_')}",
                "company": company,
                "mode": mode,
                "cadence": cadence,
                "next_run": next_run,
                "last_run": None,
                "last_score": None,
                "run_count": 0,
                "alert_email": alert_email,
                "webhook_url": webhook_url,
                "created_at": now,
                "updated_at": now,
                "status": "active",
            }
            schedules.append(schedule)

        self.save(schedules)
        logger.info(f"Schedule saved: {company} every {cadence}")
        return schedule

    def remove(self, schedule_id: str) -> bool:
        schedules = self.load()
        before = len(schedules)
        schedules = [s for s in schedules if s["id"] != schedule_id]
        if len(schedules) < before:
            self.save(schedules)
            return True
        return False

    def pause(self, schedule_id: str) -> bool:
        schedules = self.load()
        for s in schedules:
            if s["id"] == schedule_id:
                s["status"] = "paused"
                self.save(schedules)
                return True
        return False

    def resume(self, schedule_id: str) -> bool:
        schedules = self.load()
        for s in schedules:
            if s["id"] == schedule_id:
                s["status"] = "active"
                interval = CADENCE_SECONDS.get(s["cadence"], 604800)
                s["next_run"] = (datetime.now() + timedelta(seconds=interval)).isoformat()
                self.save(schedules)
                return True
        return False

    def update_after_run(self, schedule_id: str, score: int):
        schedules = self.load()
        for s in schedules:
            if s["id"] == schedule_id:
                interval = CADENCE_SECONDS.get(s["cadence"], 604800)
                s["last_run"]   = datetime.now().isoformat()
                s["last_score"] = score
                s["next_run"]   = (datetime.now() + timedelta(seconds=interval)).isoformat()
                s["run_count"]  = s.get("run_count", 0) + 1
                self.save(schedules)
                return
        self.save(schedules)

    def due_schedules(self) -> list:
        """Return schedules that are due to run right now."""
        schedules = self.load()
        now = datetime.now()
        due = []
        for s in schedules:
            if s.get("status") == "paused":
                continue
            try:
                next_run = datetime.fromisoformat(s["next_run"])
                if now >= next_run:
                    due.append(s)
            except Exception:
                continue
        return due


# ══════════════════════════════════════════════════════════════════════════════
# DIGEST ENGINE
# ══════════════════════════════════════════════════════════════════════════════
class DigestEngine:
    """
    Generates weekly/monthly digest reports summarising
    all tracked companies with score deltas.
    """

    def generate_digest(self, schedules: list) -> str:
        """Generate a plain-text digest of all scheduled companies."""
        lines = [
            "AI STACK DOCTOR — AUTOMATED DIGEST",
            f"Generated: {datetime.now().strftime('%A, %B %d %Y %H:%M UTC')}",
            "=" * 60,
            "",
        ]

        if not schedules:
            lines.append("No companies currently tracked.")
            return "\n".join(lines)

        # Group by status
        active = [s for s in schedules if s.get("status") != "paused"]
        lines.append(f"TRACKING {len(active)} COMPANIES")
        lines.append("-" * 40)

        for s in sorted(active, key=lambda x: x.get("last_score", 0) or 0,
                        reverse=True):
            score    = s.get("last_score", "—")
            last_run = s.get("last_run", "Never")
            if last_run and last_run != "Never":
                try:
                    last_run = datetime.fromisoformat(last_run).strftime("%Y-%m-%d")
                except Exception:
                    pass
            next_run = s.get("next_run", "—")
            if next_run and next_run != "—":
                try:
                    nr = datetime.fromisoformat(next_run)
                    delta = nr - datetime.now()
                    if delta.days > 0:
                        next_run = f"in {delta.days}d"
                    elif delta.seconds > 3600:
                        next_run = f"in {delta.seconds//3600}h"
                    else:
                        next_run = "soon"
                except Exception:
                    pass

            score_bar = ""
            if isinstance(score, int):
                filled = round(score / 10)
                color  = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
                score_bar = f"{color} {score}/100"

            lines.append(
                f"  {s['company'].upper():<20} "
                f"{score_bar:<15} "
                f"cadence:{s.get('cadence','weekly'):<12} "
                f"last:{last_run:<12} "
                f"next:{next_run}"
            )

        lines += ["", "=" * 60,
                  "View dashboard: https://ai-stack-doctor.onrender.com",
                  "Manage schedules: /schedules in your dashboard",
                  ""]
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# AGENTIC SCHEDULER (Main Class)
# ══════════════════════════════════════════════════════════════════════════════
class AgenticScheduler:
    """
    Fully autonomous audit scheduler.
    Runs as a background thread — start() and forget it.
    """

    CHECK_INTERVAL = 60  # seconds between schedule checks

    def __init__(self):
        self.store         = ScheduleStore()
        self.alerts        = AlertEngine()
        self.digest        = DigestEngine()
        self._thread       = None
        self._stop_event   = threading.Event()
        self._running      = False
        self._run_history  = []  # In-memory log of recent runs

    # ── Lifecycle ──────────────────────────────────────────────────────────────
    def start(self):
        """Start the scheduler background thread."""
        if self._running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="asd-scheduler",
            daemon=True,
        )
        self._thread.start()
        self._running = True
        logger.info("Agentic scheduler started ✓")

    def stop(self):
        """Stop the scheduler gracefully."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        self._running = False
        logger.info("Agentic scheduler stopped")

    @property
    def is_running(self) -> bool:
        return self._running and self._thread and self._thread.is_alive()

    # ── Main loop ──────────────────────────────────────────────────────────────
    def _loop(self):
        logger.info(f"Scheduler loop started — checking every {self.CHECK_INTERVAL}s")
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as e:
                logger.error(f"Scheduler tick error: {e}")
            self._stop_event.wait(self.CHECK_INTERVAL)

    def _tick(self):
        """Check for due schedules and run them."""
        due = self.store.due_schedules()
        if not due:
            return

        logger.info(f"Scheduler tick: {len(due)} due audit(s)")
        for schedule in due:
            self._run_scheduled_audit(schedule)

    def _run_scheduled_audit(self, schedule: dict):
        """Execute a scheduled audit and process results."""
        company = schedule["company"]
        mode    = schedule.get("mode", "competitor")
        sid     = schedule["id"]

        logger.info(f"Running scheduled audit: {company} ({mode})")
        self._log_run(company, "started", None)

        try:
            # Import agent at runtime to avoid circular imports
            from ai_stack_health_agent_v3 import (
                run_agent,
                save_to_history,
                parse_overall_from_report,
                parse_scores_from_report,
                get_last_report,
            )

            # Get previous audit for delta comparison
            prev = get_last_report(company)
            prev_score  = prev["overall"] if prev else None
            prev_scores = prev.get("scores", {}) if prev else {}

            # Run the audit
            report = run_agent(company, mode, prev)

            # Parse results
            new_score  = parse_overall_from_report(report) or 0
            new_scores = parse_scores_from_report(report) or {}

            # Save to history
            save_to_history(company, mode, report, new_score, new_scores)

            # Update schedule tracking
            self.store.update_after_run(sid, new_score)
            self._log_run(company, "completed", new_score)

            logger.info(f"Scheduled audit complete: {company} → {new_score}/100")

            # Check for alerts
            if prev_score is not None:
                alerts = self.alerts.check_for_alerts(
                    company, prev_score, new_score, prev_scores, new_scores
                )
                for alert in alerts:
                    logger.info(f"Alert triggered: {alert['message']}")
                    self.alerts.send_alert(alert)
                    # Also save alert to DB for dashboard display
                    self._save_alert_to_db(alert)

            # Send email/webhook if configured
            self._notify_completion(schedule, company, new_score, prev_score)

        except Exception as e:
            logger.error(f"Scheduled audit failed for {company}: {e}")
            self._log_run(company, "failed", None)
            # Still update next_run so we retry next cadence
            self.store.update_after_run(sid, schedule.get("last_score") or 0)

    def _notify_completion(self, schedule: dict, company: str,
                           new_score: int, prev_score: int):
        """Send completion notification if configured."""
        if not schedule.get("alert_email") and not schedule.get("webhook_url"):
            return

        delta_str = ""
        if prev_score is not None:
            delta = new_score - prev_score
            delta_str = f" (▲ +{delta}" if delta > 0 else f" (▼ {delta}" if delta < 0 else " (── unchanged"
            delta_str += ")"

        alert = {
            "type": "audit_complete",
            "severity": "info",
            "company": company,
            "message": f"{company.title()} audit complete — Score: {new_score}/100{delta_str}",
            "score": new_score,
            "prev_score": prev_score,
        }

        if schedule.get("alert_email"):
            dest = {
                "type": "email",
                "address": schedule["alert_email"],
                "smtp": self._load_smtp_config(),
            }
            try:
                self.alerts._send_email(alert, dest)
            except Exception as e:
                logger.warning(f"Completion email failed: {e}")

        if schedule.get("webhook_url"):
            dest = {"type": "webhook", "url": schedule["webhook_url"]}
            try:
                self.alerts._send_webhook(alert, dest)
            except Exception as e:
                logger.warning(f"Completion webhook failed: {e}")

    def _save_alert_to_db(self, alert: dict):
        """Save an alert to the history database for dashboard display."""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT,
                    type TEXT,
                    severity TEXT,
                    message TEXT,
                    delta INTEGER,
                    created_at TEXT
                )
            """)
            conn.execute("""
                INSERT INTO alerts (company, type, severity, message, delta, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                alert.get("company", ""),
                alert.get("type", ""),
                alert.get("severity", "info"),
                alert.get("message", ""),
                alert.get("delta", 0),
                datetime.now().isoformat(),
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to save alert to DB: {e}")

    def _load_smtp_config(self) -> dict:
        """Load SMTP config from environment variables."""
        import os
        return {
            "host":     os.environ.get("SMTP_HOST", "smtp.gmail.com"),
            "port":     int(os.environ.get("SMTP_PORT", "587")),
            "user":     os.environ.get("SMTP_USER", ""),
            "password": os.environ.get("SMTP_PASSWORD", ""),
            "from":     os.environ.get("SMTP_FROM", "alerts@ai-stack-doctor.com"),
        }

    def _log_run(self, company: str, status: str, score):
        """Add entry to in-memory run log."""
        self._run_history.append({
            "company":  company,
            "status":   status,
            "score":    score,
            "time":     datetime.now().isoformat(),
        })
        # Keep last 100 entries
        if len(self._run_history) > 100:
            self._run_history = self._run_history[-100:]

    # ── Public API ─────────────────────────────────────────────────────────────
    def schedule(self, company: str, mode: str = "competitor",
                 cadence: str = "weekly", alert_email: str = "",
                 webhook_url: str = "") -> dict:
        """Add or update a scheduled audit."""
        return self.store.add(company, mode, cadence, alert_email, webhook_url)

    def unschedule(self, schedule_id: str) -> bool:
        """Remove a scheduled audit."""
        return self.store.remove(schedule_id)

    def pause(self, schedule_id: str) -> bool:
        return self.store.pause(schedule_id)

    def resume(self, schedule_id: str) -> bool:
        return self.store.resume(schedule_id)

    def run_now(self, schedule_id: str):
        """Trigger an immediate audit for a schedule."""
        schedules = self.store.load()
        schedule  = next((s for s in schedules if s["id"] == schedule_id), None)
        if not schedule:
            return False
        thread = threading.Thread(
            target=self._run_scheduled_audit,
            args=(schedule,),
            daemon=True,
        )
        thread.start()
        return True

    def get_schedules(self) -> list:
        schedules = self.store.load()
        # Enrich with human-readable fields
        now = datetime.now()
        for s in schedules:
            try:
                nr = datetime.fromisoformat(s["next_run"])
                delta = nr - now
                if delta.total_seconds() < 0:
                    s["next_run_label"] = "Due now"
                elif delta.days > 0:
                    s["next_run_label"] = f"In {delta.days} day{'s' if delta.days != 1 else ''}"
                elif delta.seconds > 3600:
                    s["next_run_label"] = f"In {delta.seconds//3600}h"
                else:
                    s["next_run_label"] = f"In {delta.seconds//60}m"
            except Exception:
                s["next_run_label"] = "—"
            s["cadence_label"] = CADENCE_LABELS.get(s.get("cadence", "weekly"), "Weekly")
        return schedules

    def get_alerts(self, limit: int = 50) -> list:
        """Fetch recent alerts from the database."""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM alerts
                ORDER BY created_at DESC LIMIT ?
            """, (limit,)).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_run_log(self) -> list:
        """Return the in-memory run log."""
        return list(reversed(self._run_history))

    def get_digest(self) -> str:
        """Generate a digest of all scheduled companies."""
        return self.digest.generate_digest(self.store.load())

    def get_status(self) -> dict:
        schedules = self.store.load()
        return {
            "running":        self.is_running,
            "check_interval": self.CHECK_INTERVAL,
            "schedules_total": len(schedules),
            "schedules_active": len([s for s in schedules if s.get("status") != "paused"]),
            "schedules_paused": len([s for s in schedules if s.get("status") == "paused"]),
            "recent_runs":    len(self._run_history),
        }


# ── Singleton instance (shared across Flask workers) ─────────────────────────
_scheduler = None

def get_scheduler() -> AgenticScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AgenticScheduler()
    return _scheduler
