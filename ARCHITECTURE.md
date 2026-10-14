# AI Stack Doctor — Architecture

This document maps how AI Stack Doctor runs an audit, from entry point to saved report. Diagrams are written in Mermaid and render natively on GitHub.

> Reflects `ai_stack_health_agent_v3.py` (v3 core + v4 ROI layer). Update these diagrams when the audit pipeline changes.

## 1. Top-level flow

```mermaid
flowchart TD
    subgraph entry["Entry points"]
        CLI["CLI<br/>prompt_mode()"]
        API["REST API (--api)<br/>POST /audit"]
        UTIL["Utility flags<br/>--history · --set-search"]
    end

    CLI --> PREV
    API --> PREV
    UTIL -.-> CFG[("search_config.json")]
    UTIL -.-> DB

    PREV["get_last_report(company)<br/>prior audit for delta tracking"] --> AGENT
    AGENT[["run_agent(company, mode, prev)<br/>see section 2"]] --> PARSE
    PARSE["parse_overall_from_report()<br/>parse_scores_from_report()"] --> SAVE
    SAVE["save_to_history()"] --> DB[("SQLite<br/>ai_stack_history.db")]
    DB -.-> PREV
    SAVE --> OUT{"Caller"}
    OUT -->|API| JSON["JSON response<br/>overall · scores · report"]
    OUT -->|CLI| EXP["Display report<br/>optional TXT / PDF export"]
```

Audit modes selected in `prompt_mode()` or the API body: `own` (internal-facing recommendations), `competitor`, and `generic` (scored against best-practice benchmarks).

## 2. Agent loop — `run_agent()`

```mermaid
flowchart TD
    START["Build context<br/>company + mode + prior scores"] --> CALL
    CALL["Call Claude<br/>SYSTEM_PROMPT + 6 tool schemas"] --> STOP{"stop_reason"}
    STOP -->|tool_use| RT["run_tool(name, input)<br/>see section 4"]
    RT --> APPEND["Append assistant turn<br/>+ tool_result blocks"]
    APPEND --> CALL
    STOP -->|end_turn| REPORT["Return report text"]
    STOP -->|other| ERR["Return unexpected stop reason"]
```

## 3. Mandatory tool sequence

`SYSTEM_PROMPT` instructs Claude to call the six audit tools in this order before writing the report.

```mermaid
flowchart LR
    T1["1. detect_ai_stack"] --> T2["2. research_stack_health"]
    T2 --> T3["3. check_ai_integrations"]
    T3 --> T4["4. audit_governance_and_ownership"]
    T4 --> T5["5. detect_redundancies_and_gaps"]
    T5 --> T6["6. benchmark_against_peers"]
    T6 --> R["Health report<br/>scores /100 + ROI summary"]
```

## 4. Tool execution — `run_tool()`

```mermaid
flowchart TD
    IN["run_tool(tool_name, tool_input)"] --> INTEL["get_company_intel(company)<br/>COMPANY_INTEL lookup"]
    INTEL --> GEN{"Generic or<br/>My Company?"}
    GEN -->|yes| RUBRIC["Return best-practice framework text<br/>(deprecation / compliance context where relevant)"]
    GEN -->|no| Q["Build tool-specific base queries<br/>enrich_queries(base, intel)"]
    Q --> WS["web_search(query) per query<br/>ddg · google · bing · serpapi · custom<br/>falls back to DuckDuckGo on error"]
    WS --> GOV{"audit_governance_<br/>and_ownership?"}
    GOV -->|yes| CTX["Prepend get_compliance_context()<br/>get_roi_context()<br/>get_prescription_context()"]
    GOV -->|no| RET
    CTX --> RET["Return intel block + search results"]
```

## 5. Knowledge layers

| Layer | Source | Used by |
|---|---|---|
| Company intelligence | `COMPANY_INTEL` | Every tool (pre-loaded stack signals for top-tier companies) |
| Compliance catalog | `GLOBAL_COMPLIANCE` | `audit_governance_and_ownership` |
| ROI framework | `ROI_FRAMEWORK` | `audit_governance_and_ownership` → Executive ROI Summary |
| Prescriptions | `PRESCRIPTION_PRIORITY`, `QUICK_WIN_EXAMPLES` | `audit_governance_and_ownership` |
| Deprecation risk | `DEPRECATION_RISK_CATEGORIES` | `research_stack_health` (generic mode) |

## 6. REST API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/audit` | Run an audit: `{ "company": "...", "mode": "competitor" }` |
| GET | `/history` | List past audits (`?company=`, `?limit=`) |
| GET | `/history/<id>` | Fetch one saved report |
| GET | `/companies` | List companies with pre-loaded intelligence |
| POST | `/api/set-search-engine` | Set search engine and credentials |
