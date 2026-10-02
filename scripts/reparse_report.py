"""Re-parse a saved audit report and print the audit_once.py summary line.

Usage: python scripts/reparse_report.py runs/<model>_<company>_<ts>.txt

No API calls and no DB writes; reads the report file only. The model is taken
from the filename prefix (everything before the first underscore).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/reparse_report.py <report_file>")
    path = Path(sys.argv[1])
    if not path.is_file():
        sys.exit(f"Not a file: {path}")

    sys.path.insert(0, str(ROOT))
    import ai_stack_health_agent_v3 as agent

    report = path.read_text(encoding="utf-8")
    model = path.name.split("_", 1)[0]
    overall = agent.parse_overall_from_report(report)
    scores = agent.parse_scores_from_report(report)
    cats = {k: f"{v['score']}/{v['total']}" for k, v in scores.items()}
    print(
        f"model={model} overall={overall} categories={cats} "
        f"report_chars={len(report)} seconds=0.0 file={path}"
    )


if __name__ == "__main__":
    main()
