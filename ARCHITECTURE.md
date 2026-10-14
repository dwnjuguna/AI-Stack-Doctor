# AI Stack Doctor — Architecture

This document maps how AI Stack Doctor runs an audit, from entry point to saved report. Diagrams are written in Mermaid and render natively on GitHub.

> Reflects `ai_stack_health_agent_v3.py` on `main` (v4.1 REWIRED Edition, Oct 2026). Update these diagrams when the audit pipeline changes.

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
    AGENT[["run_agent(company, mode, prev)<br/>see section 2"]] --> GUARD{"Report starts<br/>with ERROR:?"}
    GUARD -->|yes| FAIL["Not saved, not exported<br/>API: HTTP 500 · CLI: print failure"]
    GUARD -->|no| PARSE["parse_overall_from_report()<br/>parse_scores_from_report()"]
    PARSE --> SAVE["save_to_history()"]
    SAVE --> DB[("SQLite<br/>ai_stack_history.db")]
    DB -.-> PREV
    SAVE --> OUT{"Caller"}
    OUT -->|API| JSON["JSON response<br/>overall · scores · report"]
    OUT -->|CLI| EXP["Display report<br/>optional TXT / PDF export"]
```

Audit modes selected in `prompt_mode()` or the API body: `own` (internal-facing recommendations), `competitor`, and `generic` (scored against best-practice benchmarks).

`parse_overall_from_report()` anchors on the `OVERALL: NN/100` line followed by its health emoji, so a "Previous Overall" mention in the delta section is never mistaken for the current score.

## 2. Agent loop — `run_agent()`

```mermaid
flowchart TD
    START["Build context<br/>company + mode + prior scores"] --> CALL
    CALL["Stream Claude call<br/>model = ASD_MODEL env var<br/>SYSTEM_PROMPT + 6 tool schemas"] --> USAGE["Accumulate token usage"]
    USAGE --> STOP{"stop_reason"}
    STOP -->|tool_use| RT["run_tool(name, input)<br/>see section 4"]
    RT --> APPEND["Append assistant turn<br/>+ tool_result blocks"]
    APPEND --> CALL
    STOP -->|end_turn| NETS[["Deterministic safety nets<br/>see section 6"]]
    NETS --> REPORT["Return report text"]
    STOP -->|max_tokens| ERR1["Return ERROR:<br/>partial output discarded"]
    STOP -->|other| ERR2["Return ERROR:<br/>unexpected stop reason"]
```

The model defaults to `claude-sonnet-4-6` when `ASD_MODEL` is unset. Token usage (calls, input, output, cache reads and writes) is logged to stderr when the loop exits, whether it succeeded or not.

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
    GEN -->|yes| RUBRIC["Return best-practice framework text<br/>(plus deprecation or governance context<br/>for the relevant tools)"]
    GEN -->|no| WHICH{"Which tool?"}
    WHICH -->|audit_governance_and_ownership| GOVT[["Governance assembly<br/>see section 5"]]
    WHICH -->|benchmark_against_peers| BQ["Base queries<br/>+ sector benchmark_hints<br/>from INDUSTRY_VALUE_MAP"]
    WHICH -->|other 4 tools| Q["Tool-specific base queries"]
    BQ --> ENR["enrich_queries(base, intel)<br/>adds intel search hints + blog site: queries"]
    Q --> ENR
    ENR --> WS["web_search(query) per query<br/>ddg · google · bing · serpapi · custom<br/>falls back to DuckDuckGo on error"]
    WS --> RET["Return intel block + search results"]
```

## 5. Governance assembly — `audit_governance_and_ownership`

This tool returns the richest context of the six. It runs ten searches, one slot for each query, grouped into three themes, and stacks six context blocks in front of the results.

```mermaid
flowchart TD
    G["audit_governance_and_ownership"] --> S1["Governance and compliance<br/>4 queries"]
    G --> S2["Ownership and org signals<br/>3 queries: CAIO, platform team,<br/>production depth"]
    G --> S3["Model provenance<br/>3 queries, one per risk factor"]
    S1 --> WS["web_search() × 10"]
    S2 --> WS
    S3 --> WS

    G --> IND{"Resolve industry slug"}
    IND -->|pre-loaded company| SLUG1["detect_industry_slug()<br/>keyword match on intel industry"]
    IND -->|not pre-loaded| SLUG2["Claude's industry_category<br/>enum choice"]
    IND -->|unknown or missing| SLUG3["default profile"]

    SLUG1 --> ICTX
    SLUG2 --> ICTX
    SLUG3 --> ICTX
    ICTX["get_industry_context()<br/>top domains · why · gap signals"]

    WS --> OUT
    CC["get_compliance_context()<br/>22 frameworks"] --> OUT
    MC["ENTERPRISE_AI_MATURITY_CONTEXT<br/>Kana + Supermetrics 2026 baselines"] --> OUT
    PC["get_model_provenance_context()<br/>3 factors + company priors"] --> OUT
    ICTX --> OUT
    RC["get_roi_context()"] --> OUT
    PR["get_prescription_context()"] --> OUT
    OUT["Combined tool result<br/>returned to Claude"]
```

## 6. Deterministic safety nets

Prompt instructions alone have occasionally failed to surface required content. Before `run_agent()` returns, the report passes through three post-processors in order. Each checks whether the model already included the content and inserts a clearly labelled fallback only if it didn't.

```mermaid
flowchart LR
    RAW["Raw report<br/>from Claude"] --> N1["ensure_governance_<br/>benchmark_line()"]
    N1 --> N2["ensure_model_<br/>provenance_lines()"]
    N2 --> N3["ensure_agentic_<br/>trajectory_line()"]
    N3 --> FINAL["Final report"]
```

| Safety net | Checks for | Scope of the check | If missing, inserts |
|---|---|---|---|
| `ensure_governance_benchmark_line()` | Both "Kana" and "Supermetrics" cited | Governance section only | Benchmark Comparator note after the Governance heading |
| `ensure_model_provenance_lines()` | Each of the 3 factors paired with Low / Medium / High / Unknown within 200 chars, never past the next factor | Governance section only | Each missing factor recorded as **Unknown** |
| `ensure_agentic_trajectory_line()` | "33%" and "routine decisions" together | Whole report | Forward-looking Kana 2026 note after the Strategic Recommendations heading |

The governance section is bounded by the next heading listed in `_SECTIONS_AFTER_GOVERNANCE`, so a citation that appears only in Peer Benchmarking doesn't count as present in Governance. Each net prints a warning to the console when it fires.

## 7. Scoring model

```mermaid
flowchart TD
    subgraph scored["Scored — 100 pts"]
        D7["7 technical domains × 13 pts<br/>GenAI · Agentic · ML · Data Eng<br/>AI Platforms · MLOps/LLMOps · Cloud AI"]
        GM["Governance Maturity — 9 pts"]
        GM --> G1["Ownership clarity 0–3"]
        GM --> G2["Published-artifact evidence 0–3"]
        GM --> G3["Confidence-vs-proof gap 0–3"]
    end
    subgraph flag["Standalone flag — not scored"]
        MP["Model Provenance & Access-Continuity"]
        MP --> F1["Vendor Access Continuity"]
        MP --> F2["Open-Weight Fallback"]
        MP --> F3["Cross-Border Exposure"]
    end
    D7 --> TOTAL["OVERALL /100<br/>Healthy 80–100 · Needs Attention 60–79 · At Risk under 60"]
    GM --> TOTAL
```

Each provenance factor gets exactly one rating: Low, Medium, High, or Unknown. **Unknown** means nothing is publicly known about the dependency. A visible dependency whose mitigation is undisclosed rates Medium or High, never Unknown. These ratings never feed the Governance Maturity /9 sub-scores.

## 8. Knowledge layers

| Layer | Source | Used by |
|---|---|---|
| Company intelligence | `COMPANY_INTEL` | Every tool (pre-loaded stack signals, search hints, engineering blogs) |
| Compliance catalog | `GLOBAL_COMPLIANCE` | `audit_governance_and_ownership` |
| Enterprise maturity baselines | `ENTERPRISE_AI_MATURITY_CONTEXT` | `audit_governance_and_ownership` → Governance Maturity /9 |
| Model provenance | `MODEL_PROVENANCE_RISK_FACTORS` | `audit_governance_and_ownership` → provenance flag |
| Industry value map | `INDUSTRY_VALUE_MAP` (10 sectors + default) | Governance (prescription weighting) and `benchmark_against_peers` (sector hints) |
| ROI framework | `ROI_FRAMEWORK` | `audit_governance_and_ownership` → Executive ROI Summary |
| Deprecation risk | `DEPRECATION_RISK_CATEGORIES` | `research_stack_health` (generic mode) |
| Maturity calibration | Inline in `SYSTEM_PROMPT` | Peer Benchmarking and AI Org Health (incl. Scaling Purgatory flag) |

## 9. REST API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/audit` | Run an audit: `{ "company": "...", "mode": "competitor" }`. Returns 500 if generation fails |
| GET | `/history` | List past audits (`?company=`, `?limit=`) |
| GET | `/history/<id>` | Fetch one saved report |
| GET | `/companies` | List companies with pre-loaded intelligence |
| POST | `/api/set-search-engine` | Set search engine and credentials |
