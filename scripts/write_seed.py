"""Build data/seed_audits.json (version 2) from the refresh run's saved reports.

Usage: python scripts/write_seed.py

Reads runs/refresh_progress.json, and for every entry (all must be "done")
re-reads the report file named in its `file` field and re-parses the overall
score and category scores from the text. No API calls and no DB writes; the
only file written is data/seed_audits.json (atomically).

generated_at is computed at runtime as the current UTC time plus one second, so
it is always newer than any existing DB row.

created_at comes from the report filename timestamp (YYYYMMDD_HHMMSS, local
time) and is written as UTC ISO-8601. The model field is intentionally not
included yet.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROGRESS_PATH = ROOT / "runs" / "refresh_progress.json"
SEED_PATH = ROOT / "data" / "seed_audits.json"

VERSION = 2
SOURCE = "claude-sonnet-4-6 refresh — 2026-10-02"
MODE = "competitor"
TS_RE = re.compile(r"_(\d{8}_\d{6})\.txt$")


def created_at_from_filename(path):
    m = TS_RE.search(path.name)
    if not m:
        sys.exit(f"No timestamp in report filename: {path.name}")
    local = datetime.strptime(m.group(1), "%Y%m%d_%H%M%S").astimezone()
    return local.astimezone(timezone.utc).isoformat()


def main():
    sys.path.insert(0, str(ROOT))
    import ai_stack_health_agent_v3 as agent

    progress = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    not_done = {c: e.get("status") for c, e in progress.items() if e.get("status") != "done"}
    if not_done:
        sys.exit(f"Entries not done, refusing to write seed: {not_done}")

    audits = []
    for company, entry in progress.items():
        path = ROOT / entry["file"]
        if not path.is_file():
            sys.exit(f"Report file missing for {company}: {path}")
        report = path.read_text(encoding="utf-8")
        overall = agent.parse_overall_from_report(report)
        scores = agent.parse_scores_from_report(report)
        if overall is None or not scores:
            sys.exit(f"Could not parse {company} from {path.name} "
                     f"(overall={overall}, categories={len(scores)})")
        audits.append({
            "company": company.strip().lower(),
            "mode": MODE,
            "overall": overall,
            "scores": scores,
            "created_at": created_at_from_filename(path),
            "report_text": report,
        })

    names = [a["company"] for a in audits]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        sys.exit(f"Duplicate companies, refusing to write seed: {dupes}")

    generated_at = (datetime.now(timezone.utc) + timedelta(seconds=1)).replace(microsecond=0).isoformat()
    snapshot = {
        "version": VERSION,
        "generated_at": generated_at,
        "source": SOURCE,
        "audits": audits,
    }
    tmp = SEED_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, SEED_PATH)
    print(f"Wrote {len(audits)} audits to {SEED_PATH.relative_to(ROOT)} "
          f"({SEED_PATH.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
