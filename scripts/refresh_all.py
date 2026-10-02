"""Re-run audits for every company in data/seed_audits.json, resumably.

Usage: python scripts/refresh_all.py [--only a,b] [--skip c,d]

- Company list: audits[*].company from data/seed_audits.json, lowercased and
  de-duplicated in order.
- Progress: runs/refresh_progress.json, {company: {status, overall, scores,
  model, chars, seconds, file, error}}. Companies whose status is "done" are
  skipped on startup; "error" entries are retried.
- Calls run_agent(company, "competitor") directly. No DB writes, and the seed
  file is never written.
- Requires ANTHROPIC_API_KEY in the environment (value is never printed).
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED_PATH = ROOT / "data" / "seed_audits.json"
RUNS_DIR = ROOT / "runs"
PROGRESS_PATH = RUNS_DIR / "refresh_progress.json"
MODE = "competitor"


def slug(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s.strip()).strip("_").lower()


def parse_names(arg):
    return [n.strip().lower() for n in arg.split(",") if n.strip()] if arg else []


def load_companies():
    audits = json.loads(SEED_PATH.read_text(encoding="utf-8")).get("audits", [])
    seen, companies = set(), []
    for a in audits:
        name = a["company"].strip().lower()
        if name and name not in seen:
            seen.add(name)
            companies.append(name)
    return companies


def load_progress():
    if PROGRESS_PATH.exists():
        try:
            return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            sys.exit(f"{PROGRESS_PATH} is not valid JSON; fix or move it before resuming.")
    return {}


def save_progress(progress):
    RUNS_DIR.mkdir(exist_ok=True)
    tmp = PROGRESS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(progress, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, PROGRESS_PATH)


def main():
    parser = argparse.ArgumentParser(description="Refresh all seed-file companies, resumably")
    parser.add_argument("--only", help="comma-separated companies to run (pilot)")
    parser.add_argument("--skip", help="comma-separated companies to skip")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set; export it and retry.")

    companies = load_companies()
    only, skip = parse_names(args.only), set(parse_names(args.skip))
    unknown = [n for n in only + sorted(skip) if n not in companies]
    if unknown:
        sys.exit(f"Not in {SEED_PATH.name}: {', '.join(unknown)}")
    if only:
        companies = [c for c in companies if c in only]
    companies = [c for c in companies if c not in skip]

    sys.path.insert(0, str(ROOT))
    import ai_stack_health_agent_v3 as agent

    model = os.environ.get("ASD_MODEL", "claude-sonnet-4-6")
    progress = load_progress()
    todo = [c for c in companies if progress.get(c, {}).get("status") != "done"]
    print(f"{len(companies)} selected, {len(companies) - len(todo)} already done, "
          f"{len(todo)} to run (model={model})")

    try:
        for i, company in enumerate(todo, 1):
            print(f"[{i}/{len(todo)}] {company} ...", flush=True)
            start = time.time()
            entry = {"status": "error", "overall": None, "scores": None, "model": model,
                     "chars": 0, "seconds": 0.0, "file": None, "error": None}
            try:
                report = agent.run_agent(company, MODE)
                entry["seconds"] = round(time.time() - start, 1)
                entry["chars"] = len(report or "")
                if not report or report.startswith("ERROR"):
                    entry["error"] = (report or "empty report")[:500]
                else:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    RUNS_DIR.mkdir(exist_ok=True)
                    path = RUNS_DIR / f"{slug(model)}_{slug(company)}_{ts}.txt"
                    path.write_text(report, encoding="utf-8")
                    entry["file"] = str(path.relative_to(ROOT))
                    entry["overall"] = agent.parse_overall_from_report(report)
                    entry["scores"] = agent.parse_scores_from_report(report)
                    if entry["overall"] is None:
                        entry["error"] = "report saved but no overall score could be parsed"
                    else:
                        entry["status"] = "done"
            except Exception as e:  # keep going; the error is recorded for the retry
                entry["seconds"] = round(time.time() - start, 1)
                entry["error"] = f"{type(e).__name__}: {e}"[:500]
            progress[company] = entry
            save_progress(progress)
            print(f"    -> {entry['status']}"
                  + (f" overall={entry['overall']}" if entry["status"] == "done" else f" ({entry['error']})"),
                  flush=True)
    except KeyboardInterrupt:
        print("\nInterrupted; progress saved. Re-run to resume.")

    rows = [(c, progress.get(c, {})) for c in companies]
    print(f"\n{'company':<28}{'model':<22}{'overall':>8}{'time(s)':>9}  status")
    for c, e in rows:
        overall = e.get("overall")
        print(f"{c:<28}{e.get('model', '-'):<22}{'-' if overall is None else overall:>8}"
              f"{e.get('seconds', '-'):>9}  {e.get('status', 'pending')}")
    done = sum(1 for _, e in rows if e.get("status") == "done")
    errs = sum(1 for _, e in rows if e.get("status") == "error")
    print(f"\ndone={done} error={errs} pending={len(rows) - done - errs}")


if __name__ == "__main__":
    main()
