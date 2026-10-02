"""Run a single audit via run_agent() and write the full report to runs/.

Usage: python scripts/audit_once.py <company> <mode>   (mode: competitor|own|generic)

Does not touch the history DB, save_to_history, or data/seed_audits.json.
Requires ANTHROPIC_API_KEY in the environment (value is never printed).
"""
import argparse
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description="Run one audit without saving to history")
    parser.add_argument("company")
    parser.add_argument("mode", choices=["competitor", "own", "generic"])
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set; export it and retry.")

    sys.path.insert(0, str(ROOT))
    import ai_stack_health_agent_v3 as agent

    model = os.environ.get("ASD_MODEL", "claude-sonnet-4-6")
    start = time.time()
    report = agent.run_agent(args.company, args.mode)
    elapsed = time.time() - start

    def slug(s):
        return re.sub(r"[^A-Za-z0-9._-]+", "_", s.strip()).strip("_").lower()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "runs"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{slug(model)}_{slug(args.company)}_{ts}.txt"
    out_path.write_text(report, encoding="utf-8")

    overall = agent.parse_overall_from_report(report)
    scores = agent.parse_scores_from_report(report)
    cats = {k: f"{v['score']}/{v['total']}" for k, v in scores.items()}
    print(
        f"model={model} overall={overall} categories={cats} "
        f"report_chars={len(report)} seconds={elapsed:.1f} file={out_path}"
    )


if __name__ == "__main__":
    main()
