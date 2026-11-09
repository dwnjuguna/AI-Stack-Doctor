# CLAUDE.md — AI Stack Doctor

Guidance for Claude Code when working in this repository. Read this before making changes.

## What this project is

AI Stack Doctor (ASD) is an open-source AI infrastructure audit tool. A Claude-powered agent runs six audit tools against a company, then produces a scored health report (0–100) with compliance flags, peer benchmarks, ROI estimates, and prioritized prescriptions. This public repo is the showcase for the project's engineering quality, so small issues (comments, wording, inconsistencies) are worth fixing.

See `ARCHITECTURE.md` for diagrams of the full audit pipeline.

## Key files

| File | Role |
|---|---|
| `ai_stack_health_agent_v3.py` | Audit agent: knowledge layers, `SYSTEM_PROMPT`, `run_tool()`, `run_agent()`, safety nets, SQLite history, CLI, REST API |
| `dashboard_server.py` | Flask backend for the web dashboard |
| `scheduler.py` | Agentic scheduler (stdlib only, no external deps) |
| `mcp_server/server.py`, `mcp_server/schemas.py` | MCP server (stdio); `schemas.py` is the single source of truth for tool contracts |
| `pdf_export.py`, `intake_reader.py` | PDF reports; intake-form-driven audits |
| `*.html` | Dashboard, guide, intake form, legal, security pages |
| `data/seed_audits.json` | Pre-computed seed audit data |

## Commands

```bash
pip3 install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."   # required
export ASD_MODEL="claude-sonnet-4-6"    # optional; this is the default

python3 ai_stack_health_agent_v3.py              # interactive CLI audit
python3 ai_stack_health_agent_v3.py --api        # REST API on :8080
python3 ai_stack_health_agent_v3.py --history    # past audits
python3 dashboard_server.py                       # dashboard on :5050
python3 -m mcp_server.server                      # MCP server (stdio)
python3 -m py_compile ai_stack_health_agent_v3.py # syntax check
```

## Verification rules

- **Paste raw stdout, never summarize it.** When reporting test runs, smoke tests, diffs, or command output, show the actual output verbatim. Summaries have hidden real defects here before.
- **Sanity check before every commit.** At minimum run `py_compile` on changed Python files. For any change to prompts, tools, parsing, or safety nets, run a live audit against a real company and review the output. Live audits have been the main way defects are found in this project.
- **Atomic commits.** One logical change per commit, with a descriptive message. Never suggest committing straight after an edit without a check.
- **Show exact before/after diffs** for proposed changes.
- **Clean DB rows with self-verifying SQL.** When fixing corrupted or duplicate rows in `ai_stack_history.db`, use `WHERE` clauses specific enough that a `SELECT` with the same clause shows exactly the rows you intend to change, and run that `SELECT` first.

## Invariants — do not break these

**Scoring**
- Total is 100: seven technical domains × 13 pts, plus Governance Maturity × 9 pts.
- Governance Maturity /9 is exactly three sub-scores of 0–3: ownership clarity, published-artifact evidence, confidence-vs-proof gap. Don't add sub-dimensions; the narrow scope is deliberate.
- Model Provenance & Access-Continuity is a standalone qualitative flag (Low / Medium / High / Unknown per factor). It must never feed the Governance Maturity score.

**Report template and post-processing**
- The safety nets (`ensure_governance_benchmark_line()`, `ensure_model_provenance_lines()`, `ensure_agentic_trajectory_line()`) find report sections by heading text. If you rename or reorder a heading in the `SYSTEM_PROMPT` report template, update `_SECTIONS_AFTER_GOVERNANCE` and every function that anchors on that heading.
- `parse_overall_from_report()` and `parse_scores_from_report()` depend on the exact `CATEGORY SCORES` and `OVERALL: NN/100 <emoji>` format. Template changes there must be checked against the parsers.
- Failed generations return a string starting with `ERROR:`. Callers must never save, export, or return these as successful reports.

**Search queries**
- Each tool slices its query list (e.g. `queries[:10]`). When adding queries, recount against the slice: `enrich_queries()` appends intel hints after the base queries, so items at the end get silently dropped.

**Data**
- ASD uses publicly available information only. Don't add ingestion of licensed, paywalled, or redistribution-restricted reports.
- Compliance frameworks, company counts, and other headline facts appear in several places (the agent, `README.md`, `security.html`, `legal.html`, dashboard pages). After changing any of them, run a repo-wide search to catch every other copy, for example `grep -rn "EU AI Act" .`. `security.html` is the copy most often left stale.

## Keep docs in sync

- When the audit pipeline changes (tools, loop, safety nets, scoring, knowledge layers), update the Mermaid diagrams in `ARCHITECTURE.md` in the same change.
- When features, counts, or commands change, update `README.md`.

## Code style

- Comments should explain *why*, especially for non-obvious fixes. Many existing comments record the bug a guard prevents; keep that practice.
- Prefer deterministic code over extra prompt instructions when the model repeatedly omits required content (this is why the safety nets exist).
