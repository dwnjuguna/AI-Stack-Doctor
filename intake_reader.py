"""
AI Stack Doctor v4 — Client Intake Reader
==========================================
Reads a completed client intake form (JSON or TXT) and runs a
personalized AI stack health audit using the client's self-reported data
as the primary source of truth alongside web research.

Usage:
    python3 intake_reader.py --file intake_acme.json
    python3 intake_reader.py --file intake_acme.txt
    python3 intake_reader.py --file intake_acme.json --export pdf

Requirements:
    Same as ai_stack_health_agent_v3.py
"""

import json
import re
import argparse
import sys
from pathlib import Path
from datetime import datetime


def load_intake(path: str) -> dict:
    """Load intake data from JSON or TXT file."""
    p = Path(path)
    if not p.exists():
        print(f"Error: File '{path}' not found.")
        sys.exit(1)

    if p.suffix.lower() == '.json':
        with open(p) as f:
            return json.load(f)

    # Parse TXT format
    data = {}
    with open(p) as f:
        content = f.read()

    # Extract key fields from TXT format
    def extract(pattern, default=''):
        m = re.search(pattern, content, re.I | re.M)
        return m.group(1).strip() if m else default

    data['companyName']    = extract(r'^COMPANY:\s*(.+)$')
    data['industry']       = extract(r'^INDUSTRY:\s*(.+)$')
    data['companySize']    = extract(r'^SIZE:\s*(.+)$')
    data['hqLocation']     = extract(r'^HQ:\s*(.+)$')
    data['revenue']        = extract(r'^REVENUE:\s*(.+)$')
    data['geoMarkets']     = extract(r'^GEOGRAPHIC MARKETS:\s*(.+)$').split(', ')
    data['llms']           = [x.strip() for x in extract(r'^LLMs / GenAI:\s*(.+)$').split(',') if x.strip() and x.strip() != 'None declared']
    data['mlFrameworks']   = [x.strip() for x in extract(r'^ML Frameworks:\s*(.+)$').split(',') if x.strip() and x.strip() != 'None declared']
    data['dataStack']      = [x.strip() for x in extract(r'^Data Engineering:\s*(.+)$').split(',') if x.strip() and x.strip() != 'None declared']
    data['cloudProviders'] = [x.strip() for x in extract(r'^Cloud Providers:\s*(.+)$').split(',') if x.strip() and x.strip() != 'None declared']
    data['mlopsTools']     = [x.strip() for x in extract(r'^MLOps / LLMOps:\s*(.+)$').split(',') if x.strip() and x.strip() != 'None declared']
    data['agenticTools']   = [x.strip() for x in extract(r'^Agentic AI:\s*(.+)$').split(',') if x.strip() and x.strip() != 'None declared']
    data['maturityLabel']  = extract(r'^Current Maturity:\s*(.+)$')
    data['targetMaturity'] = extract(r'^Target Maturity \(12mo\):\s*(.+)$')
    data['compliance']     = [x.strip() for x in extract(r'^Compliance Obligations:\s*(.+)$').split(',') if x.strip() and x.strip() != 'None declared']
    data['governance']     = [x.strip() for x in extract(r'^Governance Measures:\s*(.+)$').split(',') if x.strip() and x.strip() != 'None']
    data['teamStructure']  = extract(r'^Team Structure:\s*(.+)$')
    data['painPoints']     = extract(r'^Pain Points:\s*(.+)$')
    data['goals']          = [x.strip() for x in extract(r'^Audit Goals:\s*(.+)$').split(',') if x.strip()]
    data['competitors']    = [x.strip() for x in extract(r'^Key Competitors:\s*(.+)$').split(',') if x.strip() and x.strip() != '—']
    data['biggestConcern'] = extract(r'^Biggest Concern:\s*(.+)$')
    data['aiInitiatives']  = extract(r'^AI Initiatives \(12mo\):\s*(.+)$')
    data['additionalContext'] = extract(r'^Additional Context:\s*(.+)$')

    return data


def build_intake_context(data: dict) -> str:
    """
    Convert intake form data into a rich context block
    that gets injected into the agent's system prompt.
    """
    company = data.get('companyName', 'Unknown Company')

    llms    = ', '.join(data.get('llms', [])) or 'None declared'
    ml      = ', '.join(data.get('mlFrameworks', [])) or 'None declared'
    de      = ', '.join(data.get('dataStack', [])) or 'None declared'
    cloud   = ', '.join(data.get('cloudProviders', [])) or 'None declared'
    mlops   = ', '.join(data.get('mlopsTools', [])) or 'None declared'
    agentic = ', '.join(data.get('agenticTools', [])) or 'None declared'
    comp    = ', '.join(data.get('compliance', [])) or 'None declared'
    gov     = ', '.join(data.get('governance', [])) or 'None'
    goals   = ', '.join(data.get('goals', [])) or 'Not specified'
    competitors = ', '.join(data.get('competitors', [])) or 'Not specified'

    context = f"""
╔══════════════════════════════════════════════════════════════╗
║          CLIENT INTAKE DATA — PRIMARY SOURCE OF TRUTH        ║
╚══════════════════════════════════════════════════════════════╝

IMPORTANT: This client has completed a detailed intake form.
Use the following self-reported data as the PRIMARY source of truth.
Web search results should SUPPLEMENT this data, not replace it.
Do NOT override declared stack items with web search speculation.

COMPANY PROFILE
───────────────
Company:          {company}
Industry:         {data.get('industry', '—')}
Size:             {data.get('companySize', '—')}
HQ:               {data.get('hqLocation', '—')}
Revenue:          {data.get('revenue', '—')}
Business Model:   {', '.join(data.get('businessModel', [])) or '—'}
Geographic Markets: {', '.join(data.get('geoMarkets', [])) or '—'}
Annual AI Budget: {data.get('aiBudget', '—')}

CONFIRMED AI STACK (client-declared — HIGH CONFIDENCE)
───────────────────────────────────────────────────────
LLMs / GenAI:     {llms}
ML Frameworks:    {ml}
Data Engineering: {de}
Cloud Providers:  {cloud}
MLOps / LLMOps:   {mlops}
Agentic AI:       {agentic}

MATURITY & GOVERNANCE
─────────────────────
Current Maturity: {data.get('maturityLabel', '—')}
Target Maturity:  {data.get('targetMaturity', '—')}
Team Structure:   {data.get('teamStructure', '—')}
Governance:       {gov}
Compliance Obligations: {comp}

PAIN POINTS (client-stated — address directly in recommendations)
──────────────────────────────────────────────────────────────────
{data.get('painPoints', 'None specified')}

AUDIT GOALS (tailor report to these)
──────────────────────────────────────
{goals}

BIGGEST CONCERN
───────────────
{data.get('biggestConcern', '—')}

PLANNED AI INITIATIVES (next 12 months)
────────────────────────────────────────
{data.get('aiInitiatives', 'None specified')}

REQUESTED BENCHMARK COMPETITORS
────────────────────────────────
{competitors}

ADDITIONAL CONTEXT
──────────────────
{data.get('additionalContext', 'None')}

══════════════════════════════════════════════════════════════════
SCORING INSTRUCTIONS FOR THIS INTAKE-BASED AUDIT:
1. Score each category based on declared tools — not speculation
2. Mark declared tools as Confidence [H] — client confirmed
3. Use web search to find additional context, not to contradict intake
4. If a tool is declared but health is unknown, mark as Active/[M]
5. Recommendations MUST directly address stated pain points
6. Benchmark against declared competitors where possible
7. Flag compliance gaps against declared obligations: {comp}
8. Frame all recommendations toward stated goals: {goals}
══════════════════════════════════════════════════════════════════
"""
    return context


def run_intake_audit(intake_path: str, export: str = None):
    """Load intake file and run a personalized audit."""
    try:
        from ai_stack_health_agent_v3 import (
            run_agent, save_to_history,
            parse_overall_from_report, parse_scores_from_report,
            get_last_report, SYSTEM_PROMPT
        )
    except ImportError:
        print("Error: ai_stack_health_agent_v3.py not found in current directory.")
        sys.exit(1)

    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        RICH = True
    except ImportError:
        RICH = False
        console = None

    # Load intake data
    data = load_intake(intake_path)
    company = data.get('companyName', 'Unknown')

    if RICH:
        console.print()
        console.print(Panel(
            f"[bold cyan]Client Intake Audit[/bold cyan]\n\n"
            f"Company:  [bold]{company}[/bold]\n"
            f"Industry: {data.get('industry','—')}\n"
            f"Size:     {data.get('companySize','—')}\n"
            f"Mode:     [cyan]Own Company (Intake-enhanced)[/cyan]",
            border_style="cyan", padding=(1, 2)
        ))
    else:
        print(f"\n{'='*60}")
        print(f" AI Stack Doctor v4 — Intake Audit: {company}")
        print(f"{'='*60}")

    # Build intake context
    intake_ctx = build_intake_context(data)

    # Check for previous audit (delta tracking)
    prev = get_last_report(company)
    if prev and RICH:
        console.print(f"\n  [dim]Previous audit: {prev['date']} — Score: {prev['overall']}/100 (delta enabled)[/dim]")

    # Run agent with intake context injected
    if RICH:
        console.print(f"\n[bold]🔍 Running intake-enhanced audit for [cyan]{company}[/cyan] — 60–90 seconds...[/bold]\n")
    else:
        print(f"\n Running intake-enhanced audit for {company}...")

    # Build the user message with intake context
    user_message = (
        f"{intake_ctx}\n\n"
        f"Run a full AI stack health assessment for {company}. "
        f"This is the client's OWN company audit using intake form data. "
        f"Use the intake data above as your primary source of truth. "
        f"Focus recommendations on their stated goals and pain points."
    )
    if prev:
        user_message += (
            f"\n\nPREVIOUS AUDIT: {prev['date']} | Score: {prev['overall']}/100 | "
            f"Include SCORE DELTA section."
        )

    report = run_agent(company, 'own', prev)

    # Display report
    if RICH:
        console.print(Panel(
            report,
            title=f"[bold white]🤖 {company} — Intake-Enhanced Health Report[/bold white]",
            border_style="cyan", padding=(1, 2)
        ))
    else:
        print("\n" + "="*70)
        print(report)
        print("="*70)

    # Save to history
    overall = parse_overall_from_report(report)
    scores  = parse_scores_from_report(report)
    save_to_history(company, 'own', report, overall or 0, scores)

    if RICH:
        console.print(f"\n  [green]✓ Saved to history[/green] [dim](score: {overall}/100)[/dim]")

    # Export
    if export:
        if export in ('txt', 'both'):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"ai_stack_{company.lower().replace(' ','_')}_{ts}.txt"
            with open(fname, 'w') as f:
                f.write(report)
            msg = f"✓ TXT: {fname}"
            console.print(f"  [green]{msg}[/green]") if RICH else print(f"  {msg}")

        if export in ('pdf', 'both'):
            try:
                from pdf_export import export_report_to_pdf
                if RICH: console.print("  [dim]Generating PDF...[/dim]")
                path = export_report_to_pdf(report, company)
                msg = f"✓ PDF: {path}"
                console.print(f"  [green]{msg}[/green]") if RICH else print(f"  {msg}")
            except Exception as e:
                print(f"  PDF error: {e}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI Stack Doctor v4 — Client Intake Audit Runner"
    )
    parser.add_argument('--file',   required=True,  help="Path to intake JSON or TXT file")
    parser.add_argument('--export', default='both',
                        choices=['txt','pdf','both','none'],
                        help="Export format (default: both)")
    args = parser.parse_args()

    run_intake_audit(args.file, args.export if args.export != 'none' else None)
