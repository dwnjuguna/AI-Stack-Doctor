"""AI Stack Doctor — free-tier MCP server (stdio transport).

Exposes the three free tools (run_audit, get_audit_history, list_benchmarks)
over the Model Context Protocol on the stdio transport. No HTTP, no auth — that
is the Pro server's job (pro_server.py).

This module is a thin, stateless bridge. All real work lives in the existing
engine, ``ai_stack_health_agent_v3.py``; every tool here just validates intent,
calls the corresponding engine function(s), and shapes the result to match the
``outputSchema`` declared in ``schemas.py``. Each tool call is fully
self-contained: it carries everything it needs and leaves no session state
behind.

Run directly (``python -m mcp_server.server`` or ``python server.py``) to serve
on stdio, e.g. from a desktop MCP client's launch config.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Make the engine importable and DB-relative paths resolve, regardless of the
# working directory the MCP client launches us from.
#
# Layout:  <repo>/ai_stack_health_agent_v3.py
#          <repo>/ai_stack_history.db
#          <repo>/mcp_server/server.py   <- this file
#
# The engine opens its SQLite DB via Path("ai_stack_history.db") relative to the
# process CWD, so we both add the repo to sys.path AND chdir into it.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
os.chdir(_REPO_ROOT)

from mcp.server import Server  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402
from mcp.types import CallToolResult, TextContent, Tool  # noqa: E402

# Tool definitions (single source of truth) ---------------------------------
from mcp_server.schemas import FREE_TOOLS, TOOLS_BY_NAME  # noqa: E402

# The engine. Importing is side-effect-light: it constructs an Anthropic client
# object but makes no network call until run_agent() actually runs an audit.
import ai_stack_health_agent_v3 as engine  # noqa: E402


SERVER_NAME = "ai-stack-doctor"
SERVER_VERSION = "1.0.0"

# Free tier only ever serves these three.
_FREE_TOOL_NAMES = {tool["name"] for tool in FREE_TOOLS}


# ===========================================================================
# Errors
# ===========================================================================

class ToolError(Exception):
    """Raised by a tool handler to signal a clean, user-facing failure.

    The dispatcher converts this into a well-formed MCP error result
    (isError=True) rather than letting a raw traceback escape.
    """


# ===========================================================================
# Input validation helpers (lightweight, schema-aligned)
#
# The JSON Schema in schemas.py is the contract; many MCP clients validate
# against it before dispatch. We re-check the handful of invariants each tool
# actually depends on so the server fails cleanly even for clients that don't.
# ===========================================================================

def _require_dict(arguments: Any) -> Dict[str, Any]:
    if arguments is None:
        return {}
    if not isinstance(arguments, dict):
        raise ToolError("Tool arguments must be a JSON object.")
    return arguments


def _opt_str(args: Dict[str, Any], key: str) -> str | None:
    val = args.get(key)
    if val is None:
        return None
    if not isinstance(val, str):
        raise ToolError(f"'{key}' must be a string.")
    return val


def _opt_int(args: Dict[str, Any], key: str, *, minimum: int, maximum: int) -> int | None:
    val = args.get(key)
    if val is None:
        return None
    if isinstance(val, bool) or not isinstance(val, int):
        raise ToolError(f"'{key}' must be an integer.")
    if not (minimum <= val <= maximum):
        raise ToolError(f"'{key}' must be between {minimum} and {maximum}.")
    return val


# ===========================================================================
# Tool implementations
#
# Each returns a plain dict conforming to its tool's outputSchema. The
# dispatcher serializes the dict to JSON for the MCP result payload.
# ===========================================================================

# Map the engine's audit "mode" onto the model-agnostic environment vocabulary
# the schema exposes, and back. The engine modes are: own / competitor / generic.
_ENV_TO_MODE = {"development": "own", "staging": "own", "production": "competitor"}


def _tool_run_audit(args: Dict[str, Any]) -> Dict[str, Any]:
    """Bridge run_audit -> engine.run_agent(), persisting like the CLI does."""
    stack = args.get("stack")
    if not isinstance(stack, dict):
        raise ToolError("'stack' is required and must be an object.")
    name = stack.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ToolError("'stack.name' is required and must be a non-empty string.")
    company = name.strip()

    # Derive the engine mode from the declared environment. Default to
    # 'competitor' (external research) which matches the most common audit.
    environment = stack.get("environment")
    if company.lower() == "generic":
        mode = "generic"
    else:
        mode = _ENV_TO_MODE.get(environment, "competitor")

    persist = args.get("persist", True)
    if not isinstance(persist, bool):
        raise ToolError("'persist' must be a boolean.")

    # Pull prior report for delta tracking (engine does the same in its CLI flow).
    prev = engine.get_last_report(company) if mode != "generic" else None

    try:
        report_text = engine.run_agent(company, mode, prev)
    except Exception as exc:  # engine/LLM/network failure
        raise ToolError(f"Audit failed while running the engine: {exc}") from exc

    overall = engine.parse_overall_from_report(report_text)
    parsed_scores = engine.parse_scores_from_report(report_text)

    if persist:
        engine.save_to_history(company, mode, report_text, overall or 0, parsed_scores)

    # Shape findings from the engine's parsed category scores. The engine reports
    # per-category scores rather than discrete findings; we surface low-scoring
    # categories as findings so the output stays useful and strictly typed.
    findings: List[Dict[str, Any]] = []
    for idx, (label, detail) in enumerate(sorted(parsed_scores.items()), start=1):
        score = detail.get("score", 0)
        total = detail.get("total", 0) or 0
        ratio = (score / total) if total else 1.0
        if ratio >= 0.8:
            severity = "info"
        elif ratio >= 0.6:
            severity = "low"
        elif ratio >= 0.4:
            severity = "medium"
        elif ratio >= 0.2:
            severity = "high"
        else:
            severity = "critical"
        findings.append(
            {
                "id": f"ASD-{idx:03d}",
                "title": f"{label}: {score}/{total}",
                "severity": severity,
                "category": "quality",
                "component": label,
                "detail": (
                    f"Category '{label}' scored {score}/{total} "
                    f"(confidence {detail.get('conf', '?')})."
                ),
            }
        )

    return {
        "audit_id": f"{company.lower().replace(' ', '_')}",
        "created_at": _utc_now_iso(),
        "score": float(overall if overall is not None else 0),
        "summary": report_text,
        "findings": findings,
    }


def _tool_get_audit_history(args: Dict[str, Any]) -> Dict[str, Any]:
    """Bridge get_audit_history -> engine.list_history()/get_last_report()."""
    stack_name = _opt_str(args, "stack_name")
    min_score = args.get("min_score")
    if min_score is not None and not isinstance(min_score, (int, float)):
        raise ToolError("'min_score' must be a number.")
    limit = _opt_int(args, "limit", minimum=1, maximum=200) or 25

    rows = engine.list_history(company=stack_name, limit=limit)

    # Enrich the most recent report per company with finding counts via
    # get_last_report — keeps the bridge faithful to both engine functions.
    summaries: List[Dict[str, Any]] = []
    last_by_company: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        score = row.get("overall") or 0
        if min_score is not None and score < min_score:
            continue
        company = row.get("company", "")
        if company not in last_by_company:
            last = engine.get_last_report(company)
            last_by_company[company] = last or {}
        last = last_by_company[company]
        summaries.append(
            {
                "audit_id": str(row.get("id", "")),
                "stack_name": company,
                "created_at": _date_to_iso(row.get("date")),
                "score": float(score),
                "finding_count": len(last.get("scores", {})) if last else 0,
                "environment": _mode_to_env(row.get("mode")),
            }
        )

    return {
        "audits": summaries,
        # stdio engine returns a bounded list with no server cursor; report
        # has_more honestly based on whether we hit the requested limit.
        "page_info": {"has_more": len(rows) >= limit},
    }


def _tool_list_benchmarks(args: Dict[str, Any]) -> Dict[str, Any]:
    """Bridge list_benchmarks -> engine.COMPANY_INTEL + INDUSTRY_VALUE_MAP seed data."""
    category = _opt_str(args, "category")
    query = (_opt_str(args, "query") or "").strip().lower()
    limit = _opt_int(args, "limit", minimum=1, maximum=200) or 25

    benchmarks: List[Dict[str, Any]] = []

    # Seed set 1 — industry value map: each sector contributes a maturity
    # benchmark with its highest-value domains as reference content.
    value_map = getattr(engine, "INDUSTRY_VALUE_MAP", {})
    for sector, data in value_map.items():
        tags = " ".join(
            [sector] + data.get("top_domains", []) + data.get("benchmark_hints", [])
        ).lower()
        benchmarks.append(
            {
                "id": f"sector:{sector}",
                "name": f"{sector.replace('_', ' ').title()} AI maturity",
                "category": "maintainability",
                "unit": "score",
                "description": data.get("why", ""),
                # No numeric distribution in seed data; omit percentiles.
            }
        )
        benchmarks[-1]["_tags"] = tags  # transient; stripped before return

    # Seed set 2 — company intel: each known top-tier company contributes a
    # reference stack benchmark (its known strengths/stack as the description).
    company_intel = getattr(engine, "COMPANY_INTEL", {})
    for company, data in company_intel.items():
        if not isinstance(data, dict):
            continue
        strengths = data.get("known_strengths", [])
        tags = " ".join(
            [company, data.get("industry", "")] + strengths + data.get("known_stack", [])
        ).lower()
        benchmarks.append(
            {
                "id": f"company:{company}",
                "name": f"{company.title()} reference stack",
                "category": "quality",
                "unit": "score",
                "description": (
                    f"{data.get('industry', 'unknown sector')} — strengths: "
                    f"{', '.join(strengths) if strengths else 'n/a'}"
                ),
                "_tags": tags,
            }
        )

    # Apply filters.
    def _keep(b: Dict[str, Any]) -> bool:
        if category and b["category"] != category:
            return False
        if query and query not in (b["name"].lower() + " " + b["_tags"]):
            return False
        return True

    filtered = [b for b in benchmarks if _keep(b)]
    page = filtered[:limit]
    for b in page:
        b.pop("_tags", None)  # strip transient field; not in outputSchema

    return {
        "benchmarks": page,
        "page_info": {"has_more": len(filtered) > limit},
    }


# Dispatch table: tool name -> handler. Lookups are gated by TOOLS_BY_NAME so an
# unknown or non-free tool name can never reach a handler.
_HANDLERS = {
    "run_audit": _tool_run_audit,
    "get_audit_history": _tool_get_audit_history,
    "list_benchmarks": _tool_list_benchmarks,
}


# ===========================================================================
# Small formatting helpers
# ===========================================================================

def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _date_to_iso(date_str: Any) -> str:
    """Engine stores 'YYYY-MM-DD'; normalize to an RFC 3339 instant at midnight UTC."""
    if isinstance(date_str, str) and len(date_str) >= 10:
        return f"{date_str[:10]}T00:00:00Z"
    return _utc_now_iso()


def _mode_to_env(mode: Any) -> str:
    return {"own": "development", "competitor": "production", "generic": "staging"}.get(
        mode, "production"
    )


# ===========================================================================
# MCP server wiring
# ===========================================================================

server = Server(SERVER_NAME)


@server.list_tools()
async def list_tools() -> List[Tool]:
    """Advertise the three free-tier tools, built straight from schemas.py."""
    tools: List[Tool] = []
    for spec in FREE_TOOLS:
        tools.append(
            Tool(
                name=spec["name"],
                title=spec.get("title"),
                description=spec["description"],
                inputSchema=spec["inputSchema"],
                outputSchema=spec.get("outputSchema"),
            )
        )
    return tools


@server.call_tool()
async def call_tool(
    name: str, arguments: Dict[str, Any] | None
) -> Dict[str, Any] | CallToolResult:
    """Dispatch a tool call through TOOLS_BY_NAME and return its result.

    On success the handler returns a plain dict conforming to the tool's
    outputSchema; the low-level Server emits it as structuredContent (plus a
    JSON text block) and validates it against the schema. On failure we return
    an explicit CallToolResult with isError=True — a well-formed error result,
    never a raw traceback.
    """
    # Gate: must be a known tool AND served by the free tier.
    if name not in TOOLS_BY_NAME or name not in _FREE_TOOL_NAMES:
        return _error_result(f"Unknown or unavailable tool: {name!r}")

    handler = _HANDLERS.get(name)
    if handler is None:  # defensive: schema present but no bridge wired
        return _error_result(f"Tool {name!r} is not implemented on this server.")

    try:
        args = _require_dict(arguments)
        # Run the (synchronous, possibly long/blocking) engine bridge off the
        # event loop so the stdio transport stays responsive.
        return await asyncio.to_thread(handler, args)
    except ToolError as exc:
        return _error_result(str(exc))
    except Exception as exc:  # last-resort guard — never leak a raw traceback
        return _error_result(f"Internal error in {name!r}: {exc}")


def _error_result(message: str) -> CallToolResult:
    """Build a well-formed MCP error result with a machine-readable payload."""
    return CallToolResult(
        isError=True,
        content=[
            TextContent(
                type="text",
                text=json.dumps({"error": message}, ensure_ascii=False),
            )
        ],
    )


# ===========================================================================
# Entry point
# ===========================================================================

async def _serve() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """Serve the free tier over stdio until the client disconnects."""
    try:
        asyncio.run(_serve())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
