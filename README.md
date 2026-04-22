# 🤖 AI Stack Doctor v3

> Deep health checks for modern AI infrastructure with governance auditing, redundancy detection, peer benchmarking, and compliance assessment.

[![MIT License](https://img.shields.io/badge/License-MIT-cyan.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Powered by Claude](https://img.shields.io/badge/Powered%20by-Anthropic%20Claude-orange.svg)](https://anthropic.com)

---

## What It Does

AI Stack Doctor analyzes any company's AI infrastructure across **7 domains**, producing a structured health report with scores, peer benchmarking, governance assessment, and strategic recommendations.

| Domain | What's Assessed |
|--------|----------------|
| GenAI / LLMs | Foundation models, fine-tuning, prompt pipelines |
| Agentic AI | Orchestration frameworks, tool use, autonomous agents |
| Machine Learning | Training frameworks, model lifecycle, experimentation |
| Data Engineering | Pipelines, feature stores, streaming, warehouses |
| AI Platforms | Internal ML platforms, serving infrastructure |
| MLOps / LLMOps | CI/CD for models, monitoring, observability |
| Cloud AI Services | AWS, GCP, Azure AI services adoption |

---

## Key Features

- **22 top-tier company intelligence profiles** — Meta, Google, NVIDIA, OpenAI, Anthropic, Microsoft, Amazon, Apple, Netflix, Tesla, Adobe, Salesforce, Mistral, AMD, Oracle, Broadcom, Intel, Stability AI, DeepL, Synthesia, Aleph Alpha, ElevenLabs
- **3 audit modes** — Analyze your own company, a competitor, or run a generic best-practice audit
- **Historical tracking** — SQLite-backed audit history with score delta comparison between runs
- **14 global compliance frameworks** — EU AI Act, GDPR, CCPA, US EO on AI, HIPAA, ISO 42001, and more
- **5 configurable search engines** — DuckDuckGo (default), Google Custom Search, Bing, SerpAPI, or custom BYO
- **Dark-themed PDF export** — Executive-ready branded reports
- **REST API mode** — Expose the agent as a local endpoint for integration
- **Intelligence Dashboard** — Full trend visualization, radar comparison, compliance reference

---

## ⚠️ Public Information Notice

All company intelligence profiles, stack assessments, and scores are derived **exclusively from publicly available sources** — engineering blogs, job postings, press releases, research papers, and official product documentation.

- No proprietary, confidential, or insider information is used
- Scores are analytical estimates, not verified facts
- This tool is for informational purposes only and does not constitute legal, financial, or professional advice
- Company names and trademarks are the property of their respective owners

---

## File Structure

```
ai-stack-doctor/
├── ai_stack_health_agent_v3.py   # Main agent (CLI + REST API)
├── pdf_export.py                 # Dark-themed PDF report generator
├── dashboard_server.py           # History dashboard Flask backend
├── dashboard.html                # Intelligence dashboard (standalone)
├── search_config.json.example    # Search engine config template
├── .gitignore
├── LICENSE
└── README.md
```

---

## Quick Start

### 1. Prerequisites

```bash
# Python 3.9 or higher required
python3 --version

# Install dependencies
pip3 install anthropic ddgs rich flask reportlab
```

### 2. Set your Anthropic API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

> Get your key at [console.anthropic.com](https://console.anthropic.com)

### 3. (Optional) Configure your search engine

```bash
# Copy the example config
cp search_config.json.example search_config.json

# Default is DuckDuckGo — no API key needed
# Edit search_config.json to switch to Google, Bing, SerpAPI, or custom

# Or set via CLI flag:
python3 ai_stack_health_agent_v3.py --set-search google \
  --search-key YOUR_KEY --search-cx YOUR_ENGINE_ID
```

### 4. Run your first audit

```bash
python3 ai_stack_health_agent_v3.py
```

You'll be prompted to choose an audit mode, then enter a company name.

---

## Usage

### Interactive CLI

```bash
# Standard interactive mode
python3 ai_stack_health_agent_v3.py

# Browse past audit history
python3 ai_stack_health_agent_v3.py --history

# View history for a specific company
python3 ai_stack_health_agent_v3.py --history --company stripe
```

### REST API Mode

```bash
# Start the API server (default port 8080)
python3 ai_stack_health_agent_v3.py --api

# Run an audit
curl -X POST http://localhost:8080/audit \
  -H "Content-Type: application/json" \
  -d '{"company": "Stripe", "mode": "competitor"}'

# Get audit history
curl http://localhost:8080/history

# List companies with pre-loaded intelligence
curl http://localhost:8080/companies

# Update search engine config
curl -X POST http://localhost:8080/api/set-search-engine \
  -H "Content-Type: application/json" \
  -d '{"engine": "serpapi", "key": "your-key"}'
```

### Intelligence Dashboard

```bash
# Start the dashboard server
python3 dashboard_server.py

# Opens automatically at http://localhost:5050
# Or open dashboard.html directly in your browser for offline/demo mode
```

### Python Module

```python
from ai_stack_health_agent_v3 import run_agent, save_to_history, get_last_report
from pdf_export import export_report_to_pdf

# Run an audit programmatically
report = run_agent("Stripe", "competitor")

# Export to dark-themed PDF
pdf_path = export_report_to_pdf(report, "Stripe")
print(f"Report saved to: {pdf_path}")

# Check history
prev = get_last_report("stripe")
if prev:
    print(f"Previous score: {prev['overall']}/100 on {prev['date']}")
```

---

## Audit Modes

| Mode | Use Case | Data Leaves Machine? |
|------|----------|---------------------|
| `own` | Analyze your own company's AI stack | Only if live search enabled |
| `competitor` | Research any external company | Only if live search enabled |
| `generic` | Score against industry best practices | No |

---

## Search Engine Options

| Engine | API Key Required | Notes |
|--------|-----------------|-------|
| DuckDuckGo | No | Default, free, privacy-respecting |
| Google Custom Search | Yes | Requires Cloud project + Search Engine ID |
| Bing Search API | Yes | Requires Azure subscription |
| SerpAPI | Yes | Free tier: 100 searches/month |
| Custom / BYO | Optional | Any endpoint accepting `?q=` query param |

---

## Scoring Rubric

Each of the 7 categories is scored out of 14 points (Cloud AI Services: 16) across 5 dimensions:

| Dimension | Points | What's Measured |
|-----------|--------|----------------|
| Currency | 0–3 | Tools are recent, not deprecated |
| Coverage | 0–3 | No major capability gaps |
| Integration | 0–3 | Tools connect well, data flows cleanly |
| Governance | 0–3 | Monitoring, security, compliance, ownership |
| Maturity | 0–2 | Advanced usage, not just adoption |

**Overall health:**
- 🟢 80–100 — Healthy
- 🟡 60–79 — Needs Attention
- 🔴 Below 60 — At Risk

---

## Compliance Frameworks Covered

The tool assesses governance posture against 14 key global frameworks:

**Critical:** EU AI Act (2024), GDPR + AI, US Executive Order on AI, CCPA/CPRA, HIPAA + AI, China Generative AI Regulations

**High:** EU Data Act, Digital Services Act, NIST AI RMF, US State AI Laws, UK AI Regulation, ISO/IEC 42001, PCI-DSS v4.0, SOC 2 Type II

---

## Contributing

Contributions welcome! To add a new company to the intelligence layer, add an entry to the `COMPANY_INTEL` dictionary in `ai_stack_health_agent_v3.py` following the existing format:

```python
"company name": {
    "industry": "sector / sub-sector",
    "blogs": ["engineering.company.com/blog"],
    "known_stack": ["Tool 1", "Tool 2", ...],
    "known_strengths": ["Category 1", "Category 2"],
    "search_hints": ["targeted search query 1", ...],
},
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

Built with [Anthropic Claude](https://anthropic.com) · Open Source
