"""
AI Stack Health Agent
=====================
Analyzes a company's modern AI stack across 7 categories:
  1. GenAI / LLMs
  2. Agentic AI
  3. Machine Learning
  4. Data Engineering
  5. AI Platforms
  6. MLOps / LLMOps
  7. Cloud AI Services (AWS / Azure / GCP)

Each category is scored out of ~14 points (100 total).
Includes peer benchmarking against industry comparables.

Usage:
  python3 ai_stack_health_agent.py

Requirements:
  pip3 install anthropic ddgs
"""

import anthropic
import json

client = anthropic.Anthropic()

# ── System Prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are an elite AI infrastructure analyst specializing in assessing the modern AI stacks
of companies across seven domains: GenAI/LLMs, Agentic AI, Machine Learning, Data Engineering,
AI Platforms, MLOps/LLMOps, and Cloud AI Services.

When a user gives you a company name, you MUST use the available tools to research the company
before producing any output. Follow this exact sequence:

STEP 1 — detect_ai_stack(company_name)
STEP 2 — research_stack_health(company_name)
STEP 3 — check_ai_integrations(company_name)
STEP 4 — benchmark_against_peers(company_name, industry)

After all four tools have run, produce a full AI Stack Health Report with:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🤖  AI STACK HEALTH REPORT: [COMPANY]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OVERVIEW
  Industry | Founded | HQ | Size

STACK DETECTED
  List every AI tool/service found, grouped by category

CATEGORY SCORES  (each /14 pts, total /100)
  1. GenAI / LLMs          ██████████░░  X/14
  2. Agentic AI             ██████████░░  X/14
  3. Machine Learning       ██████████░░  X/14
  4. Data Engineering       ██████████░░  X/14
  5. AI Platforms           ██████████░░  X/14
  6. MLOps / LLMOps         ██████████░░  X/14
  7. Cloud AI Services      ████████████  X/16  ← (cloud weighted slightly higher)

  OVERALL: XX/100  🟢 Healthy | 🟡 Needs Attention | 🔴 At Risk

HEALTH RATINGS:
  🟢 Healthy         80–100
  🟡 Needs Attention 60–79
  🔴 At Risk         Below 60

CATEGORY BREAKDOWN
  For each category provide:
  - Tools detected
  - Health status & key findings
  - Risks or gaps
  - Recommended actions

PEER BENCHMARKING
  Compare against 3 industry peers. Show a simple comparison table:
  Company | Overall Score | Strongest Category | Weakest Category | Maturity Level

  Maturity levels: Experimenting → Building → Scaling → Optimizing → Leading

STRATEGIC RECOMMENDATIONS
  Top 5 prioritized actions to improve AI stack health, with estimated impact.

SCORING RUBRIC (use this internally):
  Each category is scored on:
  - Currency (tools are recent/not deprecated)     0–3 pts
  - Coverage (no major gaps in the domain)         0–3 pts
  - Integration (tools connect well together)      0–3 pts
  - Governance (monitoring, security, compliance)  0–3 pts
  - Maturity (advanced usage, not just adoption)   0–2 pts
  Cloud gets +2 bonus pts (max 16) due to its foundational role.

Do NOT fabricate tool names. Only report tools that are confirmed by research.
If a category has no detected tools, score it 0 and flag it as a critical gap.
"""

# ── Tool Definitions ───────────────────────────────────────────────────────────

tools = [
    {
        "name": "detect_ai_stack",
        "description": (
            "Searches for all AI tools, platforms, and services a company uses across "
            "7 categories: GenAI/LLMs, Agentic AI, ML frameworks, Data Engineering, "
            "AI Platforms, MLOps/LLMOps, and Cloud AI Services."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "The name of the company to research"
                }
            },
            "required": ["company_name"]
        }
    },
    {
        "name": "research_stack_health",
        "description": (
            "Researches the health status of each AI tool detected — including known issues, "
            "deprecations, version currency, security advisories, and migration alerts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "The company whose stack health is being researched"
                }
            },
            "required": ["company_name"]
        }
    },
    {
        "name": "check_ai_integrations",
        "description": (
            "Checks how well the company's AI tools are integrated with each other — "
            "data pipelines, model serving, feature stores, observability, and API connectivity."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "The company to assess for AI integration health"
                }
            },
            "required": ["company_name"]
        }
    },
    {
        "name": "benchmark_against_peers",
        "description": (
            "Finds 3 comparable companies in the same industry and benchmarks their AI stack "
            "maturity and tooling against the target company."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "The target company"
                },
                "industry": {
                    "type": "string",
                    "description": "The industry sector (e.g. retail, fintech, healthcare, SaaS)"
                }
            },
            "required": ["company_name", "industry"]
        }
    }
]

# ── Web Search Helper ──────────────────────────────────────────────────────────

def web_search(query: str, max_results: int = 6) -> str:
    """Run a DuckDuckGo search and return formatted results."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return f"No results found for: {query}"
        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(f"[{i}] {r.get('title', '')}\n    {r.get('body', '')}\n    Source: {r.get('href', '')}")
        return "\n\n".join(formatted)
    except ImportError:
        return "Error: duckduckgo_search not installed. Run: pip3 install ddgs"
    except Exception as e:
        return f"Search error: {str(e)}"


# ── Tool Execution ─────────────────────────────────────────────────────────────

def run_tool(tool_name: str, tool_input: dict) -> str:
    company = tool_input.get("company_name", "")
    industry = tool_input.get("industry", "")

    if tool_name == "detect_ai_stack":
        queries = [
            f"{company} AI technology stack LLM machine learning 2025 2026",
            f"{company} uses OpenAI Anthropic AWS SageMaker Vertex AI Databricks",
            f"{company} MLOps data engineering Airflow dbt Snowflake Spark",
            f"{company} generative AI agentic AI LangChain deployment infrastructure",
        ]
        results = [web_search(q, max_results=4) for q in queries]
        return "\n\n---\n\n".join(results)

    elif tool_name == "research_stack_health":
        queries = [
            f"{company} AI platform issues deprecations migrations 2025 2026",
            f"{company} machine learning infrastructure challenges technical debt",
            f"{company} LLM deployment problems latency cost optimization",
            f"{company} AI governance compliance responsible AI practices",
        ]
        results = [web_search(q, max_results=4) for q in queries]
        return "\n\n---\n\n".join(results)

    elif tool_name == "check_ai_integrations":
        queries = [
            f"{company} AI data pipeline architecture feature store model serving",
            f"{company} MLflow Kubeflow model registry experiment tracking",
            f"{company} LLMOps prompt monitoring observability LLM evaluation",
            f"{company} AI cloud services integration AWS Azure GCP",
        ]
        results = [web_search(q, max_results=4) for q in queries]
        return "\n\n---\n\n".join(results)

    elif tool_name == "benchmark_against_peers":
        queries = [
            f"{industry} companies AI stack maturity benchmark 2025 2026",
            f"{company} vs competitors AI technology infrastructure comparison",
            f"top {industry} companies generative AI machine learning adoption",
            f"{industry} AI leaders MLOps LLMOps best practices examples",
        ]
        results = [web_search(q, max_results=4) for q in queries]
        return "\n\n---\n\n".join(results)

    return f"Unknown tool: {tool_name}"


# ── Agent Loop ─────────────────────────────────────────────────────────────────

def run_agent(user_message: str):
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    label = list(block.input.values())[0]
                    print(f"  🔧 {block.name.replace('_', ' ').title()} — {label} ...")
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\n{block.text}\n")
            break
        else:
            print(f"Unexpected stop reason: {response.stop_reason}")
            break


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  🤖  AI Stack Health Agent")
    print("=" * 60)
    print("Analyze any company's modern AI infrastructure across:")
    print("  • GenAI / LLMs          • Agentic AI")
    print("  • Machine Learning      • Data Engineering")
    print("  • AI Platforms          • MLOps / LLMOps")
    print("  • Cloud AI Services     (AWS / Azure / GCP)")
    print()
    print("Includes peer benchmarking against industry comparables.")
    print()
    print("Type 'quit' or 'exit' to stop.")
    print("-" * 60)
    print()
    print("Examples:")
    print("  > Anthropic")
    print("  > Stripe")
    print("  > Moderna")
    print("  > JPMorgan Chase")
    print()

    while True:
        try:
            user_input = input("Which company would you like me to analyze?\n> ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "q"]:
                print("\nGoodbye! Happy building! 🤖\n")
                break

            print(f"\n🔍 Researching {user_input}'s AI stack — this may take 30–60 seconds...\n")
            run_agent(f"Run a full AI stack health assessment for {user_input}")
            print("-" * 60)
            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye! Happy building! 🤖\n")
            break


if __name__ == "__main__":
    main()
