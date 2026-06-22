"""Tool schemas for the AI Stack Doctor MCP server.

This module is the single source of truth for every tool exposed by both the
free (stdio) and Pro (Streamable HTTP) transports. It contains nothing but data:
JSON Schema (draft 2020-12) definitions for each tool's inputs and outputs.

Design constraints (enforced here, relied on by the transports):
  * Model-agnostic. No assumption about which LLM or client calls these tools.
    Schemas describe data, not prompts, and avoid any Claude/Anthropic-specific
    field, convention, or naming.
  * Strictly typed. Every object sets ``additionalProperties: False``, every
    field declares a ``type``, and constrained fields use ``enum``/``format``/
    bounds so invalid payloads are rejected before reaching tool logic.
  * Stateless. Each tool's ``inputSchema`` carries everything the tool needs to
    execute; no tool depends on a prior call within the same session. Server-side
    persistence (history, monitors) is addressed by explicit identifiers in the
    input, never by hidden session state.

Each tool entry is a dict with the keys MCP clients expect:
  name, title, description, inputSchema, outputSchema, plus a local ``tier`` key
  ("free" | "pro") the transports use to decide what to advertise.
"""

from __future__ import annotations

from typing import Any, Dict, List

# JSON Schema dialect used by every schema below.
SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"


# ---------------------------------------------------------------------------
# Reusable sub-schemas
#
# Defined once and referenced inline (by value) so each tool schema remains a
# self-contained document — MCP clients receive fully-expanded schemas with no
# external ``$ref`` resolution required.
# ---------------------------------------------------------------------------

_SEVERITY = {
    "type": "string",
    "enum": ["info", "low", "medium", "high", "critical"],
    "description": "Relative impact of a finding, lowest to highest.",
}

_ISO_TIMESTAMP = {
    "type": "string",
    "format": "date-time",
    "description": "ISO 8601 / RFC 3339 timestamp in UTC, e.g. '2026-06-22T14:30:00Z'.",
}

# A single component of an AI stack (model, vector store, orchestrator, etc.).
_STACK_COMPONENT = {
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "category"],
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 200,
            "description": "Human-readable component name, e.g. 'Postgres pgvector'.",
        },
        "category": {
            "type": "string",
            "enum": [
                "model",
                "embedding",
                "vector_store",
                "orchestration",
                "retrieval",
                "guardrails",
                "observability",
                "evaluation",
                "data_pipeline",
                "serving",
                "caching",
                "other",
            ],
            "description": "Functional role of the component within the stack.",
        },
        "version": {
            "type": "string",
            "maxLength": 100,
            "description": "Pinned version or tag of the component, if known.",
        },
        "vendor": {
            "type": "string",
            "maxLength": 200,
            "description": "Provider or maintainer of the component, if known.",
        },
        "config": {
            "type": "object",
            "description": "Opaque, component-specific configuration key/values.",
            "additionalProperties": True,
        },
    },
}

# A declarative description of the stack under audit. Self-contained so an audit
# call needs no prior state.
_STACK_DEFINITION = {
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "components"],
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 200,
            "description": "Label identifying this stack within reports.",
        },
        "description": {
            "type": "string",
            "maxLength": 2000,
            "description": "Optional free-text summary of the stack's purpose.",
        },
        "environment": {
            "type": "string",
            "enum": ["development", "staging", "production"],
            "description": "Deployment environment the stack represents.",
        },
        "components": {
            "type": "array",
            "minItems": 1,
            "maxItems": 100,
            "description": "All components that make up the stack.",
            "items": _STACK_COMPONENT,
        },
    },
}

# A single audit finding.
_FINDING = {
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "title", "severity", "category"],
    "properties": {
        "id": {
            "type": "string",
            "description": "Stable identifier for the finding (e.g. 'ASD-COST-014').",
        },
        "title": {
            "type": "string",
            "description": "Short summary of the issue.",
        },
        "severity": _SEVERITY,
        "category": {
            "type": "string",
            "enum": [
                "cost",
                "latency",
                "reliability",
                "security",
                "privacy",
                "quality",
                "scalability",
                "maintainability",
                "compliance",
            ],
            "description": "Dimension the finding relates to.",
        },
        "component": {
            "type": "string",
            "description": "Name of the component the finding applies to, if specific.",
        },
        "detail": {
            "type": "string",
            "description": "Full explanation of the finding.",
        },
        "recommendation": {
            "type": "string",
            "description": "Suggested remediation, if any.",
        },
    },
}

# Standard pagination inputs. Stateless cursor-based paging.
_PAGINATION_PROPERTIES = {
    "limit": {
        "type": "integer",
        "minimum": 1,
        "maximum": 200,
        "default": 25,
        "description": "Maximum number of records to return.",
    },
    "cursor": {
        "type": "string",
        "maxLength": 512,
        "description": "Opaque pagination cursor returned by a previous call. "
        "Omit to start from the first page.",
    },
}

# Standard pagination output block, embedded in list-returning tools.
_PAGE_INFO = {
    "type": "object",
    "additionalProperties": False,
    "required": ["has_more"],
    "properties": {
        "has_more": {
            "type": "boolean",
            "description": "True when more records exist beyond this page.",
        },
        "next_cursor": {
            "type": "string",
            "description": "Cursor to pass on the next call. Present only when has_more is true.",
        },
    },
}

# Summary record for a completed audit, used in list responses.
_AUDIT_SUMMARY = {
    "type": "object",
    "additionalProperties": False,
    "required": ["audit_id", "stack_name", "created_at", "score"],
    "properties": {
        "audit_id": {
            "type": "string",
            "description": "Unique identifier for the audit run.",
        },
        "stack_name": {
            "type": "string",
            "description": "Name of the stack that was audited.",
        },
        "created_at": _ISO_TIMESTAMP,
        "score": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
            "description": "Overall health score, 0 (worst) to 100 (best).",
        },
        "finding_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of findings produced by the audit.",
        },
        "environment": {
            "type": "string",
            "enum": ["development", "staging", "production"],
            "description": "Environment the audited stack represented.",
        },
    },
}


def _object(properties: Dict[str, Any], required: List[str]) -> Dict[str, Any]:
    """Build a strict top-level object schema with the shared dialect declared."""
    return {
        "$schema": SCHEMA_DIALECT,
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


# ===========================================================================
# FREE TIER TOOLS
# ===========================================================================

RUN_AUDIT = {
    "name": "run_audit",
    "title": "Run Stack Audit",
    "tier": "free",
    "description": (
        "Audit a described AI stack and return a health score and findings across "
        "cost, latency, reliability, security, and quality dimensions. The stack is "
        "supplied in full with the call; no prior state is required."
    ),
    "inputSchema": _object(
        properties={
            "stack": _STACK_DEFINITION,
            "checks": {
                "type": "array",
                "uniqueItems": True,
                "description": "Subset of dimensions to evaluate. Omit to run all checks.",
                "items": {
                    "type": "string",
                    "enum": [
                        "cost",
                        "latency",
                        "reliability",
                        "security",
                        "privacy",
                        "quality",
                        "scalability",
                        "maintainability",
                        "compliance",
                    ],
                },
            },
            "persist": {
                "type": "boolean",
                "default": True,
                "description": "Whether to store the result so it appears in get_audit_history.",
            },
        },
        required=["stack"],
    ),
    "outputSchema": _object(
        properties={
            "audit_id": {
                "type": "string",
                "description": "Identifier for this audit run; usable with export_report.",
            },
            "created_at": _ISO_TIMESTAMP,
            "score": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
                "description": "Overall stack health score, 0 (worst) to 100 (best).",
            },
            "summary": {
                "type": "string",
                "description": "One-paragraph natural-language assessment of the stack.",
            },
            "findings": {
                "type": "array",
                "description": "Individual issues discovered during the audit.",
                "items": _FINDING,
            },
        },
        required=["audit_id", "created_at", "score", "findings"],
    ),
}

GET_AUDIT_HISTORY = {
    "name": "get_audit_history",
    "title": "Get Audit History",
    "tier": "free",
    "description": (
        "List previously persisted audit runs, most recent first, with optional "
        "filtering by stack name and date range. Pagination is cursor-based."
    ),
    "inputSchema": _object(
        properties={
            "stack_name": {
                "type": "string",
                "maxLength": 200,
                "description": "Restrict results to audits of a stack with this exact name.",
            },
            "since": {
                **_ISO_TIMESTAMP,
                "description": "Only include audits created at or after this timestamp.",
            },
            "until": {
                **_ISO_TIMESTAMP,
                "description": "Only include audits created at or before this timestamp.",
            },
            "min_score": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
                "description": "Only include audits with at least this overall score.",
            },
            **_PAGINATION_PROPERTIES,
        },
        required=[],
    ),
    "outputSchema": _object(
        properties={
            "audits": {
                "type": "array",
                "description": "Matching audit summaries, newest first.",
                "items": _AUDIT_SUMMARY,
            },
            "page_info": _PAGE_INFO,
        },
        required=["audits", "page_info"],
    ),
}

LIST_BENCHMARKS = {
    "name": "list_benchmarks",
    "title": "List Benchmarks",
    "tier": "free",
    "description": (
        "List the reference benchmarks AI Stack Doctor scores stacks against, "
        "optionally filtered by category. Read-only catalog lookup."
    ),
    "inputSchema": _object(
        properties={
            "category": {
                "type": "string",
                "enum": [
                    "cost",
                    "latency",
                    "reliability",
                    "security",
                    "privacy",
                    "quality",
                    "scalability",
                    "maintainability",
                    "compliance",
                ],
                "description": "Restrict the catalog to a single dimension.",
            },
            "query": {
                "type": "string",
                "maxLength": 200,
                "description": "Case-insensitive substring match on benchmark name or tags.",
            },
            **_PAGINATION_PROPERTIES,
        },
        required=[],
    ),
    "outputSchema": _object(
        properties={
            "benchmarks": {
                "type": "array",
                "description": "Matching benchmark definitions.",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "name", "category", "unit"],
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Stable benchmark identifier.",
                        },
                        "name": {
                            "type": "string",
                            "description": "Human-readable benchmark name.",
                        },
                        "category": {
                            "type": "string",
                            "description": "Dimension the benchmark measures.",
                        },
                        "unit": {
                            "type": "string",
                            "description": "Unit of the benchmark value, e.g. 'ms', 'USD/1M tokens', 'score'.",
                        },
                        "description": {
                            "type": "string",
                            "description": "What the benchmark measures and how.",
                        },
                        "percentiles": {
                            "type": "object",
                            "additionalProperties": False,
                            "description": "Reference distribution across audited stacks.",
                            "properties": {
                                "p50": {"type": "number"},
                                "p90": {"type": "number"},
                                "p99": {"type": "number"},
                            },
                        },
                    },
                },
            },
            "page_info": _PAGE_INFO,
        },
        required=["benchmarks", "page_info"],
    ),
}


# ===========================================================================
# PRO TIER TOOLS
# ===========================================================================

COMPARE_STACKS = {
    "name": "compare_stacks",
    "title": "Compare Stacks",
    "tier": "pro",
    "description": (
        "Compare two or more AI stacks side by side and return per-dimension "
        "deltas plus an overall recommendation. Stacks may be supplied inline as "
        "definitions or referenced by the id of a previously persisted audit."
    ),
    "inputSchema": _object(
        properties={
            "stacks": {
                "type": "array",
                "minItems": 2,
                "maxItems": 10,
                "description": "The stacks to compare, given inline or by audit reference.",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "description": "Exactly one of 'definition' or 'audit_id' must be set.",
                    "oneOf": [
                        {"required": ["definition"]},
                        {"required": ["audit_id"]},
                    ],
                    "properties": {
                        "label": {
                            "type": "string",
                            "maxLength": 200,
                            "description": "Display label for this entry in the comparison.",
                        },
                        "definition": _STACK_DEFINITION,
                        "audit_id": {
                            "type": "string",
                            "description": "Reference to a persisted audit to reuse its scored stack.",
                        },
                    },
                },
            },
            "dimensions": {
                "type": "array",
                "uniqueItems": True,
                "description": "Dimensions to compare on. Omit to compare on all.",
                "items": {
                    "type": "string",
                    "enum": [
                        "cost",
                        "latency",
                        "reliability",
                        "security",
                        "privacy",
                        "quality",
                        "scalability",
                        "maintainability",
                        "compliance",
                    ],
                },
            },
        },
        required=["stacks"],
    ),
    "outputSchema": _object(
        properties={
            "entries": {
                "type": "array",
                "description": "Per-stack scores, aligned by index with the request.",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["label", "score"],
                    "properties": {
                        "label": {"type": "string"},
                        "score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "dimension_scores": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 100,
                            },
                            "description": "Score per evaluated dimension keyed by dimension name.",
                        },
                    },
                },
            },
            "winner_label": {
                "type": "string",
                "description": "Label of the highest-scoring stack overall.",
            },
            "recommendation": {
                "type": "string",
                "description": "Natural-language guidance explaining the comparison outcome.",
            },
        },
        required=["entries", "recommendation"],
    ),
}

SCHEDULE_MONITORING = {
    "name": "schedule_monitoring",
    "title": "Schedule Monitoring",
    "tier": "pro",
    "description": (
        "Create or replace a recurring monitor that re-audits a stack on a schedule "
        "and raises alerts when its score crosses a threshold. The full stack and "
        "schedule are supplied with the call."
    ),
    "inputSchema": _object(
        properties={
            "monitor_id": {
                "type": "string",
                "maxLength": 200,
                "description": "Provide to update an existing monitor; omit to create a new one.",
            },
            "stack": _STACK_DEFINITION,
            "schedule": {
                "type": "object",
                "additionalProperties": False,
                "required": ["frequency"],
                "description": "When the monitor re-runs the audit.",
                "properties": {
                    "frequency": {
                        "type": "string",
                        "enum": ["hourly", "daily", "weekly", "monthly"],
                        "description": "How often the audit re-runs.",
                    },
                    "hour_utc": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 23,
                        "description": "UTC hour to run for daily/weekly/monthly schedules.",
                    },
                    "day_of_week": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 6,
                        "description": "0=Monday..6=Sunday, for weekly schedules.",
                    },
                },
            },
            "alert": {
                "type": "object",
                "additionalProperties": False,
                "required": ["score_below"],
                "description": "Condition and destination for alerts.",
                "properties": {
                    "score_below": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "Raise an alert when the audit score drops below this value.",
                    },
                    "channels": {
                        "type": "array",
                        "uniqueItems": True,
                        "description": "Delivery channels for the alert.",
                        "items": {
                            "type": "string",
                            "enum": ["email", "webhook", "slack"],
                        },
                    },
                    "webhook_url": {
                        "type": "string",
                        "format": "uri",
                        "description": "Destination URL when 'webhook' is among the channels.",
                    },
                },
            },
            "enabled": {
                "type": "boolean",
                "default": True,
                "description": "Whether the monitor is active on creation/update.",
            },
        },
        required=["stack", "schedule"],
    ),
    "outputSchema": _object(
        properties={
            "monitor_id": {
                "type": "string",
                "description": "Identifier of the created or updated monitor.",
            },
            "status": {
                "type": "string",
                "enum": ["created", "updated"],
                "description": "Whether a new monitor was created or an existing one replaced.",
            },
            "enabled": {"type": "boolean"},
            "next_run_at": {
                **_ISO_TIMESTAMP,
                "description": "When the monitor will next execute.",
            },
        },
        required=["monitor_id", "status", "enabled", "next_run_at"],
    ),
}

GET_COMPETITOR_ALERTS = {
    "name": "get_competitor_alerts",
    "title": "Get Competitor Alerts",
    "tier": "pro",
    "description": (
        "Retrieve alerts about tracked competitor stacks — new components, benchmark "
        "movements, and notable changes — with optional filtering by competitor and "
        "severity. Read-only, paginated."
    ),
    "inputSchema": _object(
        properties={
            "competitor": {
                "type": "string",
                "maxLength": 200,
                "description": "Restrict alerts to a single tracked competitor by name.",
            },
            "min_severity": {
                **_SEVERITY,
                "description": "Only include alerts at or above this severity.",
            },
            "since": {
                **_ISO_TIMESTAMP,
                "description": "Only include alerts generated at or after this timestamp.",
            },
            **_PAGINATION_PROPERTIES,
        },
        required=[],
    ),
    "outputSchema": _object(
        properties={
            "alerts": {
                "type": "array",
                "description": "Competitor alerts, newest first.",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "competitor", "severity", "title", "detected_at"],
                    "properties": {
                        "id": {"type": "string"},
                        "competitor": {"type": "string"},
                        "severity": _SEVERITY,
                        "title": {"type": "string"},
                        "detail": {"type": "string"},
                        "change_type": {
                            "type": "string",
                            "enum": [
                                "component_added",
                                "component_removed",
                                "benchmark_improved",
                                "benchmark_regressed",
                                "pricing_changed",
                                "other",
                            ],
                            "description": "Nature of the detected change.",
                        },
                        "detected_at": _ISO_TIMESTAMP,
                    },
                },
            },
            "page_info": _PAGE_INFO,
        },
        required=["alerts", "page_info"],
    ),
}

EXPORT_REPORT = {
    "name": "export_report",
    "title": "Export Report",
    "tier": "pro",
    "description": (
        "Render a persisted audit as a downloadable report in the requested format. "
        "Returns either inline content or a time-limited download URL depending on size."
    ),
    "inputSchema": _object(
        properties={
            "audit_id": {
                "type": "string",
                "description": "Identifier of the audit to export.",
            },
            "format": {
                "type": "string",
                "enum": ["pdf", "html", "markdown", "json", "csv"],
                "description": "Output format for the rendered report.",
            },
            "include_recommendations": {
                "type": "boolean",
                "default": True,
                "description": "Whether to include remediation guidance in the report.",
            },
            "redact_config": {
                "type": "boolean",
                "default": False,
                "description": "Redact component config values from the export.",
            },
        },
        required=["audit_id", "format"],
    ),
    "outputSchema": _object(
        properties={
            "audit_id": {"type": "string"},
            "format": {
                "type": "string",
                "enum": ["pdf", "html", "markdown", "json", "csv"],
            },
            "delivery": {
                "type": "string",
                "enum": ["inline", "url"],
                "description": "How the report is returned: inline content or a download URL.",
            },
            "content": {
                "type": "string",
                "description": "Report content when delivery is 'inline'. Base64 for binary formats.",
            },
            "content_encoding": {
                "type": "string",
                "enum": ["utf-8", "base64"],
                "description": "Encoding of the inline content field.",
            },
            "download_url": {
                "type": "string",
                "format": "uri",
                "description": "Time-limited URL when delivery is 'url'.",
            },
            "expires_at": {
                **_ISO_TIMESTAMP,
                "description": "Expiry of the download URL, when delivery is 'url'.",
            },
        },
        required=["audit_id", "format", "delivery"],
    ),
}

GET_TEAM_AUDITS = {
    "name": "get_team_audits",
    "title": "Get Team Audits",
    "tier": "pro",
    "description": (
        "List audits across an entire team's workspace, optionally filtered by member "
        "and date range. Requires the caller's API key to be authorized for the team."
    ),
    "inputSchema": _object(
        properties={
            "team_id": {
                "type": "string",
                "minLength": 1,
                "maxLength": 200,
                "description": "Identifier of the team whose audits to list.",
            },
            "member": {
                "type": "string",
                "maxLength": 200,
                "description": "Restrict results to audits run by this team member identifier.",
            },
            "since": {
                **_ISO_TIMESTAMP,
                "description": "Only include audits created at or after this timestamp.",
            },
            "until": {
                **_ISO_TIMESTAMP,
                "description": "Only include audits created at or before this timestamp.",
            },
            **_PAGINATION_PROPERTIES,
        },
        required=["team_id"],
    ),
    "outputSchema": _object(
        properties={
            "team_id": {"type": "string"},
            "audits": {
                "type": "array",
                "description": "Audit summaries across the team, newest first.",
                "items": {
                    **_AUDIT_SUMMARY,
                    "required": _AUDIT_SUMMARY["required"] + ["member"],
                    "properties": {
                        **_AUDIT_SUMMARY["properties"],
                        "member": {
                            "type": "string",
                            "description": "Identifier of the team member who ran the audit.",
                        },
                    },
                },
            },
            "page_info": _PAGE_INFO,
        },
        required=["team_id", "audits", "page_info"],
    ),
}


# ===========================================================================
# Registries
#
# The transports import these. server.py advertises FREE_TOOLS only; pro_server.py
# advertises ALL_TOOLS. Lookups go through TOOLS_BY_NAME.
# ===========================================================================

FREE_TOOLS: List[Dict[str, Any]] = [
    RUN_AUDIT,
    GET_AUDIT_HISTORY,
    LIST_BENCHMARKS,
]

PRO_TOOLS: List[Dict[str, Any]] = [
    COMPARE_STACKS,
    SCHEDULE_MONITORING,
    GET_COMPETITOR_ALERTS,
    EXPORT_REPORT,
    GET_TEAM_AUDITS,
]

ALL_TOOLS: List[Dict[str, Any]] = FREE_TOOLS + PRO_TOOLS

TOOLS_BY_NAME: Dict[str, Dict[str, Any]] = {tool["name"]: tool for tool in ALL_TOOLS}


__all__ = [
    "SCHEMA_DIALECT",
    "FREE_TOOLS",
    "PRO_TOOLS",
    "ALL_TOOLS",
    "TOOLS_BY_NAME",
    "RUN_AUDIT",
    "GET_AUDIT_HISTORY",
    "LIST_BENCHMARKS",
    "COMPARE_STACKS",
    "SCHEDULE_MONITORING",
    "GET_COMPETITOR_ALERTS",
    "EXPORT_REPORT",
    "GET_TEAM_AUDITS",
]
