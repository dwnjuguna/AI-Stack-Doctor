# AI Stack Doctor — MCP Server Specification

> **Status: Design Phase** — Implementation target Q3 2026
> 
> This document specifies the Model Context Protocol (MCP) server for AI Stack Doctor.
> Once built, any enterprise using Claude, ChatGPT, or any MCP-compatible AI platform
> can call AI Stack Doctor audits directly from within their AI workflow — no browser required.

---

## Why an MCP Server?

The State of Martech 2026 report (Brinker & Riemersma) documents 29,000+ MCP servers
built in just 18 months — more than twice the entire martech landscape took 15 years to reach.
Anthropic's Claude Connectors already feature dozens of martech tools. An AI Stack Doctor
MCP server would make our audit API callable from:

- Claude (via Claude Connectors / claude.ai)
- ChatGPT (via ChatGPT Apps)
- Any MCP-compatible agent framework (LangChain, CrewAI, AutoGPT)
- Enterprise internal AI assistants

This is a distribution channel that costs ~40 hours to build and gives us reach into
every enterprise already using an LLM platform.

---

## MCP Server Architecture

```
MCP Server: ai-stack-doctor-mcp
Transport:  HTTP/SSE (Server-Sent Events)
Base URL:   https://mcp.ai-stack-doctor.com  (future)
Auth:       Bearer token (Pro/Enterprise API key)
```

---

## Tools Exposed

### Tool 1: `run_audit`
Run a full AI stack audit on any company.

```json
{
  "name": "run_audit",
  "description": "Run a complete AI stack health audit on any company. Returns a scored report (0-100) across 7 AI domains with competitor benchmarks, compliance flags, and prioritized recommendations with ROI estimates.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "company": {
        "type": "string",
        "description": "Company name to audit (e.g. 'Stripe', 'Nubank', 'your own company name')"
      },
      "mode": {
        "type": "string",
        "enum": ["competitor", "own", "generic"],
        "description": "Audit mode: 'competitor' for benchmarking a competitor, 'own' for your own company, 'generic' for best-practices assessment",
        "default": "competitor"
      }
    },
    "required": ["company"]
  }
}
```

**Returns:**
```json
{
  "company": "Stripe",
  "overall_score": 90,
  "score_band": "Healthy",
  "domains": {
    "GenAI_LLMs": {"score": 13, "total": 14},
    "Agentic_AI": {"score": 12, "total": 14},
    "Machine_Learning": {"score": 14, "total": 14},
    "Data_Engineering": {"score": 13, "total": 14},
    "AI_Platforms": {"score": 12, "total": 14},
    "MLOps_LLMOps": {"score": 13, "total": 14},
    "Cloud_AI_Services": {"score": 13, "total": 16}
  },
  "top_prescriptions": [...],
  "compliance_flags": [...],
  "report_url": "https://ai-stack-doctor.onrender.com/report/stripe_20260520"
}
```

---

### Tool 2: `get_score`
Get the latest score for a company from audit history (no new audit run).

```json
{
  "name": "get_score",
  "description": "Get the most recent AI stack health score for a company from audit history. Fast — no new audit required.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "company": {
        "type": "string",
        "description": "Company name"
      }
    },
    "required": ["company"]
  }
}
```

---

### Tool 3: `compare_companies`
Compare two companies side-by-side across all 7 AI domains.

```json
{
  "name": "compare_companies",
  "description": "Compare two companies' AI stack health scores across all 7 domains. Useful for competitive analysis and benchmarking.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "company_a": {"type": "string"},
      "company_b": {"type": "string"}
    },
    "required": ["company_a", "company_b"]
  }
}
```

---

### Tool 4: `get_compliance_flags`
Get compliance risk flags for a company based on geography and industry.

```json
{
  "name": "get_compliance_flags",
  "description": "Get AI compliance risk flags for a company across 14 global frameworks including EU AI Act, GDPR+AI, CMMC, FedRAMP, and HIPAA+AI.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "company": {"type": "string"},
      "region": {
        "type": "string",
        "enum": ["us", "europe", "asia", "latam", "africa", "global"],
        "default": "global"
      },
      "industry": {"type": "string", "description": "e.g. fintech, healthcare, retail"}
    },
    "required": ["company"]
  }
}
```

---

### Tool 5: `list_companies`
List all 44 pre-loaded company profiles with their latest scores.

```json
{
  "name": "list_companies",
  "description": "List all pre-loaded company intelligence profiles with latest AI stack health scores. Filter by region or industry.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "region": {
        "type": "string",
        "enum": ["us", "europe", "asia", "latam", "africa"],
        "description": "Filter by region (optional)"
      },
      "industry": {
        "type": "string",
        "description": "Filter by industry (optional)"
      }
    }
  }
}
```

---

### Tool 6: `get_deprecation_risks`
Identify tools in a company's stack that are at deprecation or consolidation risk.

```json
{
  "name": "get_deprecation_risks",
  "description": "Identify AI tools in a company's stack that are at high risk of deprecation or being absorbed by major AI platforms (based on State of Martech 2026 data). Returns estimated annual spend at risk.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "company": {"type": "string"},
      "tools": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Optional: provide known tool list for faster analysis"
      }
    },
    "required": ["company"]
  }
}
```

---

## Implementation Plan

### Phase 1 — Basic MCP Server (Q3 2026, ~40 hours)
```
- FastAPI or Flask SSE endpoint
- Tools: run_audit, get_score, compare_companies, list_companies
- Auth: Bearer token (Pro API key)
- Deploy: Render.com or Railway
- Register: PulseMCP, Glama, mcp.so directories
- Submit: Anthropic Claude Connectors program
```

### Phase 2 — Enhanced MCP Server (Q4 2026, ~60 hours)
```
- Tools: get_compliance_flags, get_deprecation_risks
- Streaming support (audit runs ~90s — stream progress events)
- Webhook callbacks for long-running audits
- Rate limiting by tier
- Usage analytics
```

### Phase 3 — Enterprise MCP Server (2027)
```
- Private deployment option (run in customer's infrastructure)
- RBAC — scoped to specific companies
- Gov Edition MCP (air-gap capable, FedRAMP compliant)
- Custom company profile injection via MCP
```

---

## Example Claude Connector Usage

Once registered, a Claude user could say:

> *"Run an AI stack audit on Stripe and compare it with Adyen"*

Claude would call:
1. `run_audit("Stripe", "competitor")`
2. `run_audit("Adyen", "competitor")`
3. `compare_companies("Stripe", "Adyen")`

And return a complete competitive intelligence report — all powered by AI Stack Doctor,
without the user ever opening a browser.

---

## Registration Targets

Once built, register on:
- [PulseMCP](https://pulsemcp.com) — largest MCP directory
- [Glama](https://glama.ai/mcp/servers) — curated AI tool registry
- [mcp.so](https://mcp.so) — community MCP directory
- [Anthropic Claude Connectors](https://claude.ai/connectors) — official program
- [OpenAI GPT Actions](https://platform.openai.com/docs/actions) — ChatGPT integration
- [AWS Marketplace](https://aws.amazon.com/marketplace) — enterprise distribution (Phase 3)

---

*Built with ❤️ using the Anthropic Claude SDK*
*"I am because we are." — Ubuntu*
