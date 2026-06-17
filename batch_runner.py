"""
AI Stack Doctor — Batch Runner
===============================
Runs a full v4 audit on every company in COMPANY_INTEL and saves results
to ai_stack_history.db. Run once locally to pre-populate the dashboard.

Usage:
    python3 batch_runner.py              # run all 44 companies
    python3 batch_runner.py --limit 5   # run first 5 (for testing)
    python3 batch_runner.py --skip "meta,google"  # skip specific companies
"""

import argparse
import time
from datetime import datetime
from ai_stack_health_agent_v3 import (
    COMPANY_INTEL,
    run_agent,
    save_to_history,
    parse_overall_from_report,
    parse_scores_from_report,
    get_last_report,
)

def run_batch(limit: int = None, skip: list = None):
    skip = [s.strip().lower() for s in (skip or [])]
    companies = [c for c in COMPANY_INTEL.keys() if c not in skip]
    if limit:
        companies = companies[:limit]

    total = len(companies)
    print(f"\n{'='*60}")
    print(f"AI Stack Doctor — Batch Runner v4")
    print(f"Companies to audit: {total}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    success = 0
    failed = []

    for i, company in enumerate(companies, 1):
        print(f"[{i}/{total}] Auditing: {company.title()} ...", flush=True)
        start = time.time()
        try:
            prev = get_last_report(company)
            report = run_agent(company, "competitor", prev)
            overall = parse_overall_from_report(report)
            scores = parse_scores_from_report(report)
            save_to_history(company, "competitor", report, overall or 0, scores)
            elapsed = round(time.time() - start)
            print(f"  ✓ Done in {elapsed}s — Score: {overall}/100")
            success += 1
        except Exception as e:
            elapsed = round(time.time() - start)
            print(f"  ✗ Failed after {elapsed}s — {e}")
            failed.append((company, str(e)))

        # Polite pause between audits to avoid rate limits
        if i < total:
            print(f"  Waiting 10s before next audit...", flush=True)
            time.sleep(10)

    print(f"\n{'='*60}")
    print(f"Batch complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Succeeded: {success}/{total}")
    if failed:
        print(f"Failed ({len(failed)}):")
        for company, err in failed:
            print(f"  - {company}: {err}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Stack Doctor Batch Runner")
    parser.add_argument("--limit", type=int, help="Only run first N companies (for testing)")
    parser.add_argument("--skip", type=str, help="Comma-separated companies to skip")
    args = parser.parse_args()

    skip_list = args.skip.split(",") if args.skip else []
    run_batch(limit=args.limit, skip=skip_list)
