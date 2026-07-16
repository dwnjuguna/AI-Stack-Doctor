# 🤖 AI Stack Doctor v4.1

> **Know exactly where your AI infrastructure stands — in 90 seconds.**

[![License: MIT](https://img.shields.io/badge/License-MIT-cyan.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Powered by Claude](https://img.shields.io/badge/Powered%20by-Anthropic%20Claude-orange.svg)](https://www.anthropic.com)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-ai--stack--doctor.onrender.com-green.svg)](https://ai-stack-doctor.onrender.com)

AI Stack Doctor is a free, open-source AI infrastructure audit tool that gives any company a complete health check of their AI stack — with scores, peer benchmarks, ROI estimates, compliance flags, and a prioritized action plan. Built for consultants, executives, and technical teams. No technical background required.

---

## 📊 Why This Exists — The Data

From the **State of Martech 2026** (Brinker & Riemersma, n=208 marketing & martech leaders):

| Stat | Finding |
|------|---------|
| **88 / 130** | Marketing leaders NOT using AI to manage their own stack — highest gap of any AI use case surveyed |
| **Only 8%** | Of organizations report full confidence in their AI governance readiness |
| **73%** | Have a formal GenAI policy — but a policy is not a finish line |
| **7.1%** | Growth in Governance, Compliance & Privacy tools — one of only 11 subcategories growing |
| **−37 net** | Content Marketing tools lost — first wave of AI content tools being absorbed by major platforms |

> *"A policy is a starting point, not a finish line — and the gap between 'we have a policy' and 'we have the infrastructure to enforce it' is where most organizations are still working things out."*
> — State of Martech 2026

**AI Stack Doctor fills that gap.** Free. In 90 seconds.

---


## 🚦 Free vs Pro — What's Available Where

AI Stack Doctor follows the **open source engine / hosted service** model.
The code is MIT — free forever. The cloud service is where the business value lives.

| Feature | Open Source (Self-Host) | Hosted Free | Pro Tier | Team Tier | Enterprise |
|---------|------------------------|-------------|----------|-----------|------------|
| CLI audit agent | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| Basic PDF export | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| Single audit run | ✅ | ✅ | ✅ | ✅ | ✅ |
| Self-hosted dashboard | ✅ Full | — | — | — | — |
| Audit history & trends | ✅ Self-hosted | — | 🔒 Pro | 🔒 Pro | 🔒 Enterprise |
| All 44 company profiles | ✅ Self-hosted | 10 profiles | 🔒 Pro | 🔒 Pro | 🔒 Enterprise |
| Agentic scheduler | ✅ Self-hosted | — | 🔒 Pro | 🔒 Pro | 🔒 Enterprise |
| Enhanced prescriptions | ✅ Self-hosted | Basic only | 🔒 Pro | 🔒 Pro | 🔒 Enterprise |
| Cohort filtering | ✅ Self-hosted | — | 🔒 Pro | 🔒 Pro | 🔒 Enterprise |
| Branded PDF export | ✅ Self-hosted | — | 🔒 Pro | 🔒 Pro | 🔒 Enterprise |
| API access | ✅ Self-hosted | — | 🔒 Pro | 🔒 Pro | 🔒 Enterprise |
| Team workspace | — | — | — | 🔒 Team | 🔒 Enterprise |
| White-label reports | — | — | — | 🔒 Team | 🔒 Enterprise |
| Custom company profiles | — | — | — | 🔒 Team | 🔒 Enterprise |
| SSO / SAML | — | — | — | — | 🔒 Enterprise |
| Gov Edition | — | — | — | — | 🔒 Gov |
| Dedicated CSM + SLA | — | — | — | — | 🔒 Enterprise |

### 💡 The Model Explained

**Self-hosters** get everything — you bring your own Anthropic API key and run your own server.
That is the spirit of open source and we fully support it.

**Hosted service** users get a managed, always-on experience with cloud history,
scheduling, and team features — without managing infrastructure.

> **Pro, Team, and Enterprise tiers are currently in development.**
> Pricing and availability will be announced at launch.
> Join the waitlist to be first to know and get early access.

**[→ Join the Pro Waitlist](https://ai-stack-doctor.onrender.com/guide#waitlist)**
**[→ Register Government Interest](https://ai-stack-doctor.onrender.com/security#government)**

---

## 🌐 Live Demo

| URL | Description |
|-----|-------------|
| [ai-stack-doctor.onrender.com](https://ai-stack-doctor.onrender.com) | Intelligence Dashboard |
| [/guide](https://ai-stack-doctor.onrender.com/guide) | Non-Technical User Guide |
| [/intake](https://ai-stack-doctor.onrender.com/intake) | Smart Client Intake Form |
| [/legal](https://ai-stack-doctor.onrender.com/legal) | Legal & Privacy |
| [/security](https://ai-stack-doctor.onrender.com/security) | Security Posture |

---

## ✨ What's New in v4.1

| Feature | Description |
|---------|-------------|
| 🏭 **Industry Intelligence** | 10 sector profiles — prescriptions weighted by highest-value AI domains per industry |
| 🩺 **AI Org Health** | New report section: CAIO signals, AI platform team, production depth |
| ⚠️ **Scaling Purgatory Flag** | Sharpened maturity ladder — detects companies stuck between Scaling and Optimizing |
| 🔍 **Sector Benchmark Hints** | Peer comparisons enriched with industry-specific search signals |
| 🎯 **Smart Intake Forms** | 4 persona-tailored forms — Consultant, Executive, Marketer, General |
| 💰 **ROI Layer** | Every recommendation includes gap cost, fix cost, projected ROI, payback period |
| 📖 **User Guide** | Beautiful non-technical landing page at `/guide` with research-backed stats |
| ⚡ **Quick Readiness Check** | 5-question self-check on `/guide`, instant tier result, no email required — free-tier entry point before the full audit |
| 🌍 **44 Company Profiles** | US, Europe, Asia, Latin America, Africa — including first-ever African AI benchmarks |
| 🔍 **Cohort Filtering** | Filter by industry (28 categories), size, and region |
| ⏱️ **Agentic Scheduler** | Autonomous audit scheduling, change detection, and alerts |
| 🔒 **Security Foundation** | Auth scaffolding, audit logging, Gov Edition roadmap |
| ⚖️ **Full Legal Layer** | GDPR, CCPA, EU AI Act, Data Processing Agreement |
| 📉 **Deprecation Risk Intel** | Flags tools at high risk of being absorbed by major AI platforms |
| 🔌 **MCP Server (Live)** | Free-tier Model Context Protocol server — run audits, pull history, and list benchmarks from Claude Desktop over stdio |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AI STACK DOCTOR v4.1                         │
│                  ai-stack-doctor.onrender.com                        │
└──────────────────────────┬──────────────────────────────────────────┘
                            │
           ┌────────────────┼──────────────────────┐
           │                │                      │
           ▼                ▼                      ▼
    ┌─────────────┐  ┌─────────────────┐  ┌───────────────────┐
    │  /          │  │  /guide         │  │  /intake          │
    │  dashboard  │  │  landing page   │  │  4-persona form   │
    │  .html      │  │  guide.html     │  │  intake_form.html │
    └──────┬──────┘  └─────────────────┘  └────────┬──────────┘
           │                                        │
           ▼                                        ▼
    ┌───────────────────────────────────────────────────────────┐
    │               dashboard_server.py  (Flask)                 │
    │                                                            │
    │  31 Routes across 8 categories:                            │
    │  ├── Pages   /  /guide  /intake  /legal  /security        │
    │  ├── Data    /api/summary  /companies  /trend  /compare   │
    │  ├── Intake  /api/intake/submit                            │
    │  ├── Auth    /api/auth/generate-key  /keys  /revoke        │
    │  ├── Logs    /api/audit-log                                │
    │  ├── Lists   /api/waitlist  /api/gov-interest              │
    │  └── Sched   /api/scheduler/* (10 routes)                 │
    └──────────────────────┬────────────────────────────────────┘
                            │
           ┌────────────────┼────────────────────┐
           │                │                    │
           ▼                ▼                    ▼
    ┌─────────────┐  ┌──────────────────┐  ┌───────────────┐
    │ scheduler   │  │ ai_stack_health  │  │  SQLite DB    │
    │ .py         │  │ _agent_v3.py     │  │  history.db   │
    │             │  │                  │  │               │
    │ Classes:    │  │  6 Audit Tools:  │  │  Tables:      │
    │ Agentic     │  │  ├─detect_stack  │  │  ├─ audits    │
    │ Scheduler   │  │  ├─research      │  │  ├─ alerts    │
    │ AlertEngine │  │  ├─integrations  │  │  └─ history   │
    │ DigestEngine│  │  ├─governance    │  │               │
    │ ScheduleStore│ │  ├─redundancy    │  │  Files:       │
    └──────┬──────┘  │  └─benchmark     │  │  schedules    │
           │         └────────┬─────────┘  │  .json        │
           │                  │            └───────────────┘
           └──────────────────┤
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────┐
    │                  EXTERNAL SERVICES                       │
    │                                                          │
    │  ┌──────────────────┐   ┌────────────────────────────┐  │
    │  │  Anthropic API   │   │  Search (configurable)     │  │
    │  │  Claude Sonnet   │   │  ├─ DuckDuckGo (default)   │  │
    │  │  AI analysis     │   │  ├─ Google Custom Search   │  │
    │  └──────────────────┘   │  ├─ Bing / SerpAPI         │  │
    │                         │  └─ Private / Custom        │  │
    │                         └────────────────────────────┘  │
    └─────────────────────────────────────────────────────────┘
```

---

## 🤖 Agent Architecture

The audit agent uses a **6-tool agentic loop** powered by Anthropic Claude:

```
User Input (company + mode)
        │
        ▼
┌────────────────────────────────────────────────────────┐
│                  AGENTIC AUDIT LOOP                     │
│                                                         │
│  Tool 1: detect_ai_stack                                │
│  └─ 8 targeted searches across 7 technical domains      │
│     GenAI/LLMs · Agentic · ML · Data Eng               │
│     AI Platforms · MLOps · Cloud AI                     │
│     (governance is scored separately as an 8th category)│
│                                                         │
│  Tool 2: research_stack_health                          │
│  └─ Deprecations · vendor stability · G2 data           │
│     + State of Martech 2026 deprecation risk intel      │
│                                                         │
│  Tool 3: check_ai_integrations                          │
│  └─ Pipeline health · data flows · observability        │
│                                                         │
│  Tool 4: audit_governance_and_ownership                 │
│  └─ 22 compliance frameworks + ROI context              │
│     + AI Org Health: CAIO, platform team, prod depth    │
│     + Industry-weighted priority context                │
│                                                         │
│  Tool 5: detect_redundancies_and_gaps                   │
│  └─ Capability overlaps · wasted spend                  │
│                                                         │
│  Tool 6: benchmark_against_peers                        │
│  └─ 3-company comparison from 44 intel profiles         │
│                                                         │
└────────────────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────────────┐
│                    REPORT OUTPUT                        │
│                                                         │
│  Executive Summary + ROI Table                          │
│  Stack Inventory (confirmed tools)                      │
│  Deprecation Risk Flags (State of Martech 2026)         │
│  Category Scores (8 categories / 100 pts)               │
│  Category Deep Dives                                    │
│  Governance & Compliance Health                         │
│  Peer Benchmarking                                      │
│  Strategic Recommendations + Full ROI Analysis          │
│  Enhanced Prescriptions with Priority Matrix            │
│  Audit Confidence Summary                               │
│                                                         │
│  Export: TXT  ·  PDF (dark-themed)  ·  Dashboard        │
└────────────────────────────────────────────────────────┘
```

---

## 📊 Scoring System

```
DOMAIN                   WEIGHT    WHAT IT MEASURES
────────────────────────────────────────────────────────
GenAI / LLMs              13 pts   Foundation models, RAG, fine-tuning
Agentic AI                13 pts   Autonomous agents, orchestration
Machine Learning          13 pts   Training frameworks, model lifecycle
Data Engineering          13 pts   Pipelines, warehouses, feature stores
AI Platforms              13 pts   Internal ML platforms, model serving
MLOps / LLMOps            13 pts   Monitoring, observability, CI/CD
Cloud AI Services         13 pts   AWS/GCP/Azure AI services maturity
Governance Maturity        9 pts   Ownership clarity, published-artifact evidence, confidence-vs-proof gap
────────────────────────────────────────────────────────
TOTAL                    100 pts

🟢 Healthy          80–100
🟡 Needs Attention  60–79
🔴 At Risk           < 60
```

---

## 🏭 Industry Value Map (REWIRED Edition)

v4.1 is the **REWIRED Edition** — calibrated on the methodology from *Rewired: The McKinsey Guide to Outcompeting in the Age of Digital and AI* (Lamarre, Smaje & Zemmel). The core idea: **not every AI domain is worth the same to every industry.** A fraud-detection ML stack is table stakes for a neobank and a footnote for a media company.

The `INDUSTRY_VALUE_MAP` encodes **10 sector profiles** (plus a default fallback). Each profile prioritizes the audit's prescriptions toward the domains that drive the most value for that sector:

```
SECTOR               HIGHEST-VALUE AI DOMAINS
──────────────────────────────────────────────────────────
Fintech              Machine Learning · Data Engineering · MLOps
Healthcare           AI Platforms · Governance · Machine Learning
E-commerce           GenAI/LLMs · Machine Learning · Data Engineering
Media                GenAI/LLMs · Agentic AI · MLOps
Enterprise Software  Agentic AI · GenAI/LLMs · Cloud AI
Semiconductors       AI Platforms · Machine Learning · Cloud AI
Logistics            Machine Learning · Data Engineering · Agentic AI
Telecom              Data Engineering · Machine Learning · Cloud AI
Social Media         Machine Learning · Data Engineering · MLOps
Marketing / MarTech  Data Engineering · GenAI/LLMs · Governance
```

Each profile carries:

- **`top_domains`** — the highest-value domains used to weight prescription priority
- **`why`** — the business rationale (e.g. *"Fraud detection, credit scoring, and real-time decisioning are table-stakes competitive advantages"*)
- **`benchmark_hints`** — sector-specific search signals that enrich peer benchmarking
- **`gap_signals`** — concrete capabilities the auditor probes for (e.g. *real-time inference <50ms*, *AML model monitoring*)

The map also feeds the **Scaling Purgatory** maturity calibration (REWIRED's "death by pilots" signal), sharpening detection of companies stuck between Scaling and Optimizing. Add a sector by extending `INDUSTRY_VALUE_MAP` in the agent.

---

## 📉 Deprecation Risk Intelligence

Powered by **State of Martech 2026** data (Brinker & Riemersma):

```
HIGH RISK — Being absorbed by ChatGPT / Claude / Gemini:
  Jasper · Copy.ai · Writesonic · Anyword · Persado
  Phrasee · Lately.ai · Lumen5 · Rytr

MEDIUM RISK — Major platforms building equivalent features:
  Grammarly Business AI · standalone SEO AI writers
  basic AI personalization engines

WATCH LIST — Categories under pressure:
  Sales Automation point solutions  (-23 net tools in 2026)
  Social Media AI monitoring        (-8 net)
  Live Chat standalone AI           (-23 net)
  Video Marketing AI tools          (-14 net)
```

Every audit now flags at-risk tools and estimates annual spend at risk from consolidation.

---

## 🌍 Company Intelligence Coverage

**44 pre-loaded company profiles across 5 regions and 28 industries:**

### 🇺🇸 United States (17)
Google · Microsoft · NVIDIA · Meta · OpenAI · Anthropic · Netflix · Tesla · Apple · Amazon · Mistral · Salesforce · Adobe · AMD · Oracle · Broadcom · Intel

### 🇪🇺 Europe (10)
Stability AI · DeepL · Synthesia · Aleph Alpha · ElevenLabs · DeepMind · Revolut · Adyen · Klarna · Wise

### 🌏 Asia (9)
Baidu · ByteDance · Alibaba · Samsung · DeepSeek · Infosys · Ant Group · Paytm · Kakao

### 🌎 Latin America (5)
Nubank · Mercado Libre · Rappi · Clip · Ualá

### 🌍 Africa (3)
Flutterwave · Safaricom (M-Pesa) · Moniepoint

> 🏆 **First AI benchmarking tool in the world with African company profiles.**

---

## 🔒 Compliance Frameworks (22)

**Critical:** EU AI Act (2024, incl. 2026 Omnibus) · GDPR+AI · US EO 14409 (June 2026) · CCPA/CPRA · HIPAA+AI · China GenAI Regs · CMMC 2.0 · FedRAMP 20x

**High:** EU Data Act · Digital Services Act · NIST AI RMF · UK AI Regulation · ISO 42001 · PCI-DSS v4.0 · SOC 2 · Texas TRAIGA · California TFAIA · California ADMT · Colorado SB 26-189 (ADMT) · Connecticut AI Safety Act · South Korea AI Framework Act · Saudi Arabia PDPL + AI Framework

---

## 🚀 Quick Start

### Prerequisites
```bash
python3 --version    # 3.11+
pip3 install anthropic ddgs rich flask reportlab gunicorn
```

### 1. Clone & Configure
```bash
git clone https://github.com/dwnjuguna/AI-Stack-Doctor
cd AI-Stack-Doctor

# Get your API key at console.anthropic.com
export ANTHROPIC_API_KEY="sk-ant-..."

# Make it permanent (Mac/Linux)
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc && source ~/.zshrc
```

### 2. Run the CLI Agent
```bash
python3 ai_stack_health_agent_v3.py
```

### 3. Run the Full Dashboard
```bash
python3 dashboard_server.py
# Opens at http://localhost:5050
```

### 4. Run a Client Intake Audit
```bash
# First send client to: http://localhost:5050/intake/consultant
# They fill the form and download intake_company.json
# Then run:
python3 intake_reader.py --file intake_acme.json --export both
```

---

## 📁 File Structure

```
ai-stack-doctor/
│
├── 🤖  ai_stack_health_agent_v3.py  # Main audit agent (CLI + API + 44 companies)
├── 📄  pdf_export.py                # Dark-themed PDF report generator
├── 📋  intake_reader.py             # Client intake → personalized audit runner
│
├── 🌐  dashboard_server.py          # Flask backend (31 routes)
├── ⏱️  scheduler.py                 # Agentic scheduler (zero external deps)
│
├── 🔌  mcp_server/                  # MCP server (free tier, live)
│   ├── server.py                   #   stdio transport — 3 free tools
│   └── schemas.py                  #   tool contracts (free + Pro), single source of truth
│
├── 📦  data/
│   └── seed_audits.json            # Pre-computed audit seed data (REWIRED v4 batch)
│
├── 🎨  dashboard.html               # Intelligence dashboard (44 companies)
├── 📝  intake_form.html             # Smart 4-persona intake form
├── 📖  guide.html                   # Non-technical user guide
├── ⚖️  legal.html                   # Legal & privacy (GDPR/CCPA/EU AI Act)
├── 🔒  security.html                # Security posture & Gov Edition
│
├── ⚙️  requirements.txt             # Python dependencies
├── ☁️  render.yaml                  # Render.com deployment config
├── 🔐  .env.example                 # Environment variable template
└── 📚  README.md                    # This file

# Auto-created at runtime:
# ai_stack_history.db     SQLite audit history & alerts
# schedules.json          Agentic scheduler configuration
# audit_log.jsonl         Append-only tamper-evident audit trail
# api_keys.json           Pro tier API key store
# gov_interest.json       Government Edition interest registrations
# intake_submissions/     Client intake JSON files
```

---

## 🎯 Intake Form — 4 Personas

Send clients a tailored link before your first call:

| Persona | URL | Time | Best For |
|---------|-----|------|----------|
| **Consultant** | `/intake/consultant` | ~10 min | Client engagements, gap analysis |
| **C-Suite / Exec** | `/intake/executive` | ~8 min | Board-ready reports, compliance risk |
| **Marketer / CMO** | `/intake/marketer` | ~7 min | MarTech AI stack, content AI audit, deprecated tool detection |
| **General** | `/intake/general` | ~5 min | Quick self-assessment |

The **Marketer persona** now includes a **Content AI Stack Audit** module — identifying tools at deprecation risk based on State of Martech 2026 data, and asking whether the stack is "AI everywhere, integrated nowhere."

Intake data = **high-confidence ground truth**. The agent uses it as primary source over web research.

---

## ⏱️ Agentic Scheduler

Zero external dependencies — pure Python stdlib:

```python
from scheduler import get_scheduler

sched = get_scheduler()
sched.start()  # Starts background daemon thread

# Schedule weekly Stripe audit with Slack webhook
sched.schedule(
    company     = "Stripe",
    mode        = "competitor",
    cadence     = "weekly",       # hourly/daily/weekly/monthly/quarterly
    webhook_url = "https://hooks.slack.com/..."
)

# Trigger immediate on-demand audit
sched.run_now(schedule_id)

# Get change-detection alerts (fires when score moves 3+ pts)
alerts = sched.get_alerts()

# Get digest of all tracked companies
print(sched.get_digest())
```

---

## 💰 ROI Layer

Every recommendation includes:

```
Gap Cost:      $150K–$500K/year  ← what inaction is costing
Fix Cost:      ~$40K             ← investment to resolve
Projected ROI: 350% / 12 months
Payback:       3 months
Quick Win:     Enable LangSmith free tier this week — zero cost
```

9 ROI domains with evidence-based benchmarks:
GenAI/LLMs · Agentic AI · Machine Learning · Data Engineering ·
AI Platforms · MLOps/LLMOps · Cloud AI Services · Governance · Redundancy

---

## 🔌 MCP Server

AI Stack Doctor ships a working **Model Context Protocol (MCP) server** — call the audit engine directly from Claude, or any MCP-compatible agent, without leaving the chat. The free tier is **live today** over stdio; Pro-tier tools are in development.

```
Free tier — live now (stdio, Claude Desktop):
  run_audit           → Full 90-second audit on any company
  get_audit_history   → Past audits with scores and finding counts
  list_benchmarks     → Sector + company reference benchmarks

Pro tier — in development (Streamable HTTP, any MCP client):
  compare_stacks       → Side-by-side multi-company comparison
  schedule_monitoring  → Recurring autonomous audits
  get_competitor_alerts → Change-detection alerts
  export_report        → Branded PDF export
  get_team_audits      → Shared team workspace history
```

The implementation lives in [`mcp_server/`](mcp_server/) — `server.py` (stdio transport) and `schemas.py` (the tool contracts, the single source of truth for both tiers). Setup instructions are in **[MCP Integration](#-mcp-integration-connect-claude-desktop)** below.

> **Context:** The State of Martech 2026 report documents 29,000+ MCP servers built in 18 months —
> more than twice the entire martech landscape took 15 years to reach. This is a real distribution channel.

---

## 🔒 Security

| Control | Status |
|---------|--------|
| HTTPS / TLS | ✅ Live |
| Public information only | ✅ Live |
| GDPR cookie consent | ✅ Live |
| Privacy policy + legal | ✅ Live |
| EU AI Act disclosure | ✅ Live |
| Private Server / Air-gap mode | ✅ Live |
| API key authentication | ⚙️ In Progress |
| Audit logging | ⚙️ In Progress |
| SSO / SAML | 📅 Planned |
| FedRAMP 20x | 🔮 Roadmap |
| CMMC 2.0 | 🔮 Roadmap |

Full posture → [/security](https://ai-stack-doctor.onrender.com/security)

### 🏛️ Government Edition

Purpose-built for defense contractors and federal agencies. Separate infrastructure. Air-gap capable. AWS GovCloud. FIPS 140-2. NIST 800-171. FedRAMP 20x pathway.

[Register Interest →](https://ai-stack-doctor.onrender.com/security#government)

---

## 🌐 Deploy to Render.com

1. Fork this repo on GitHub
2. Create a new **Web Service** on [render.com](https://render.com)
3. Connect your GitHub fork
4. Add environment variable: `ANTHROPIC_API_KEY` = `sk-ant-...`
5. Build command: `pip install -r requirements.txt`
6. Start command: `gunicorn dashboard_server:app`
7. Deploy → live in ~3 minutes

---

## 📡 REST API

```bash
# Start local API server
python3 ai_stack_health_agent_v3.py --api

# Run an audit via POST
curl -X POST http://localhost:8080/audit \
  -H "Content-Type: application/json" \
  -d '{"company": "Stripe", "mode": "competitor"}'

# Get audit history
curl http://localhost:8080/history

# List all tracked companies
curl http://localhost:8080/companies
```

---

## 🤝 Contributing

Contributions are very welcome! Priority areas:

- **New company profiles** — add to `COMPANY_INTEL` in the agent
- **New industry profiles** — add sector intelligence to `INDUSTRY_VALUE_MAP` in the agent
- **New compliance frameworks** — extend `GLOBAL_COMPLIANCE`
- **New regions** — Middle East, Southeast Asia, South Asia
- **Local LLM support** — Ollama / LM Studio integration
- **MCP Pro-tier tools** — implement the HTTP transport in `mcp_server/` (schemas already defined in `schemas.py`)
- **Translations** — guide.html in other languages
- **UI improvements** — dashboard, intake form, guide

```bash
git clone https://github.com/dwnjuguna/AI-Stack-Doctor
cd AI-Stack-Doctor
pip3 install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
python3 dashboard_server.py
```

---

## 📄 License

MIT License — free to use, modify, and distribute.

> Company names and trademarks referenced in audit reports belong to their respective owners.
> All scores are analytical estimates derived from publicly available information only.
> Not legal, financial, or professional advice.
> State of Martech 2026 data cited with attribution to Scott Brinker & Frans Riemersma.

---

## 🙏 Acknowledgements

- [Anthropic](https://www.anthropic.com) — Claude AI powering the entire audit engine
- [DuckDuckGo](https://duckduckgo.com) — Privacy-respecting default search
- [Render.com](https://render.com) — Hosting infrastructure
- [Chart.js](https://chartjs.org) — Dashboard data visualizations
- [IBM Plex Mono](https://fonts.google.com/specimen/IBM+Plex+Mono) — Terminal typography
- [Bebas Neue](https://fonts.google.com/specimen/Bebas+Neue) — Display typography
- [Scott Brinker & Frans Riemersma](https://chiefmartec.com) — State of Martech 2026 research
- [Eric Lamarre, Kate Smaje & Rodney Zemmel](https://www.wiley.com/en-us/Rewired) — *Rewired: The McKinsey Guide to Outcompeting in the Age of Digital and AI* — industry intelligence framework and maturity calibration methodology
- The open source community — for making tools like this possible

---

## 🔌 MCP Integration (Connect Claude Desktop)

AI Stack Doctor speaks the **Model Context Protocol (MCP)** — the open standard that lets AI assistants call external tools directly. Connect it to Claude Desktop and you can run a full stack audit, pull peer benchmarks, and review your audit history without ever leaving the chat — Claude calls the engine for you and reasons over the results in real time.

### Prerequisites

- **Python 3.11+**
- **Claude Desktop** installed ([download](https://claude.ai/download))
- **`ANTHROPIC_API_KEY`** set in your environment — the audit engine runs on Claude

### Install

```bash
# 1. Clone the repo
git clone https://github.com/dwnjuguna/AI-Stack-Doctor.git && cd AI-Stack-Doctor

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy the config below into Claude Desktop's config file, then restart Claude Desktop
#    macOS:   ~/Library/Application Support/Claude/claude_desktop_config.json
#    Windows: %APPDATA%\Claude\claude_desktop_config.json
```

### `claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ai-stack-doctor": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/absolute/path/to/AI-Stack-Doctor",
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-your-key-here"
      }
    }
  }
}
```

### Try it

Once connected, just ask Claude in plain English:

> - *"Audit Stripe's AI stack"*
> - *"Show me benchmarks for fintech companies"*
> - *"What audits have I run recently?"*

The free tier exposes three tools — `run_audit`, `get_audit_history`, and `list_benchmarks` — over stdio.

### 🚀 Going Pro

The free tier connects to **Claude Desktop** only. **The Pro tier** *(coming soon)* — hosted — adds **scheduled monitoring**, **team workspaces**, **competitor alerts**, and **branded PDF exports**, served over Streamable HTTP for **any MCP client**.

| Tier | Transport | Works with |
|------|-----------|------------|
| **Free** | stdio | Claude Desktop |
| **Pro** | Streamable HTTP | Any MCP client — LangChain, LlamaIndex, OpenAI Assistants, custom |

---

<div align="center">

---

### Built with ❤️ using the [Anthropic Claude SDK](https://docs.anthropic.com/en/api/getting-started)

*"I am because we are." — Ubuntu*

Built with responsibility, ethics, dignity, integrity, and respect.
Open source. Free forever. Global by design.

---

[🌐 Live Demo](https://ai-stack-doctor.onrender.com) &nbsp;·&nbsp;
[📖 User Guide](https://ai-stack-doctor.onrender.com/guide) &nbsp;·&nbsp;
[🔒 Security](https://ai-stack-doctor.onrender.com/security) &nbsp;·&nbsp;
[⚖️ Legal](https://ai-stack-doctor.onrender.com/legal) &nbsp;·&nbsp;
[🐙 GitHub](https://github.com/dwnjuguna/AI-Stack-Doctor)

</div>
