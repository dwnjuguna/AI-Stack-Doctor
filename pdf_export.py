"""
AI Stack Doctor v2 — PDF Export Module (Dark Theme Fix)
========================================================
Converts the plain-text health report into a polished, dark-themed PDF.

Usage (standalone):
    python3 pdf_export.py --input report.txt --company Stripe

Usage (as module):
    from pdf_export import export_report_to_pdf
    path = export_report_to_pdf(report_text, company_name)

Requirements:
    pip3 install reportlab
"""

import re
import os
import sys
import argparse
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.pdfgen import canvas as pdfcanvas

# ── Palette ───────────────────────────────────────────────────────────────────
C_BG      = colors.HexColor("#0D1117")   # page background
C_BG2     = colors.HexColor("#080C10")   # header/footer bar
C_SURFACE = colors.HexColor("#141B24")   # card backgrounds
C_BORDER  = colors.HexColor("#1E2D3D")   # subtle borders
C_GRID    = colors.HexColor("#151E2A")   # grid line texture
C_CYAN    = colors.HexColor("#00C8E0")   # primary accent
C_GREEN   = colors.HexColor("#10B981")   # healthy
C_YELLOW  = colors.HexColor("#F59E0B")   # warning
C_RED     = colors.HexColor("#EF4444")   # at-risk
C_WHITE   = colors.HexColor("#E2E8F0")   # primary text
C_LIGHT   = colors.HexColor("#C9D1D9")   # body text
C_MUTED   = colors.HexColor("#64748B")   # muted text
C_SUB     = colors.HexColor("#94A3B8")   # sub text

HEX_CYAN   = "#00C8E0"
HEX_GREEN  = "#10B981"
HEX_YELLOW = "#F59E0B"
HEX_RED    = "#EF4444"
HEX_WHITE  = "#E2E8F0"
HEX_LIGHT  = "#C9D1D9"

PAGE_W, PAGE_H = letter
MARGIN = 0.65 * inch
INNER_W = PAGE_W - 2 * MARGIN


# ── Score helpers ─────────────────────────────────────────────────────────────
def score_color(score, total):
    pct = score / total
    if pct >= 0.8: return C_GREEN,  HEX_GREEN
    if pct >= 0.6: return C_YELLOW, HEX_YELLOW
    return C_RED, HEX_RED


# ── Page chrome: drawn BEFORE content on each page ───────────────────────────
def draw_page_background(canvas, doc):
    """Draws the dark background and chrome. Called before platypus content."""
    canvas.saveState()
    w, h = PAGE_W, PAGE_H

    # 1. Full page dark fill
    canvas.setFillColor(C_BG)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)

    # 2. Subtle dot-grid texture (very faint)
    canvas.setStrokeColor(C_GRID)
    canvas.setLineWidth(0.3)
    for y in range(36, int(h - 42), 28):
        canvas.line(0, y, w, y)

    # 3. Top bar
    canvas.setFillColor(C_BG2)
    canvas.rect(0, h - 44, w, 44, fill=1, stroke=0)
    # Cyan accent strip
    canvas.setFillColor(C_CYAN)
    canvas.rect(0, h - 46, w, 2, fill=1, stroke=0)
    # Logo text
    canvas.setFillColor(C_CYAN)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(MARGIN, h - 27, "AI STACK DOCTOR")
    canvas.setFillColor(C_MUTED)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(MARGIN + 122, h - 27, "v2  |  Infrastructure Health Report")
    # Company top-right
    if hasattr(doc, '_company') and doc._company:
        canvas.setFillColor(C_SUB)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(w - MARGIN, h - 27, doc._company.upper())

    # 4. Bottom bar
    canvas.setFillColor(C_BG2)
    canvas.rect(0, 0, w, 34, fill=1, stroke=0)
    canvas.setFillColor(C_CYAN)
    canvas.rect(0, 34, w, 1, fill=1, stroke=0)
    # Page number
    canvas.setFillColor(C_MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(w / 2, 12, f"Page {doc.page} of {doc._page_count}")
    canvas.drawString(MARGIN, 12, f"Generated: {doc._generated}")
    canvas.drawRightString(w - MARGIN, 12, "CONFIDENTIAL  |  AI Stack Doctor")

    canvas.restoreState()


def draw_page_background_later(canvas, doc):
    """Alias — same fn, ReportLab calls both onPage variants."""
    draw_page_background(canvas, doc)


# ── Styles ────────────────────────────────────────────────────────────────────
def build_styles():
    return {
        "cover_title": ParagraphStyle(
            "cover_title", fontName="Helvetica-Bold",
            fontSize=32, textColor=C_WHITE, leading=38,
            alignment=TA_CENTER, spaceAfter=6),

        "cover_sub": ParagraphStyle(
            "cover_sub", fontName="Helvetica",
            fontSize=13, textColor=C_CYAN, leading=20,
            alignment=TA_CENTER, spaceAfter=4),

        "cover_company": ParagraphStyle(
            "cover_company", fontName="Helvetica-Bold",
            fontSize=26, textColor=C_CYAN, leading=32,
            alignment=TA_CENTER),

        "cover_meta": ParagraphStyle(
            "cover_meta", fontName="Helvetica",
            fontSize=9, textColor=C_MUTED, leading=16,
            alignment=TA_CENTER),

        "h1": ParagraphStyle(
            "h1", fontName="Helvetica-Bold",
            fontSize=14, textColor=C_CYAN, leading=18,
            spaceBefore=16, spaceAfter=6),

        "h2": ParagraphStyle(
            "h2", fontName="Helvetica-Bold",
            fontSize=11, textColor=C_WHITE, leading=15,
            spaceBefore=10, spaceAfter=4),

        "h3": ParagraphStyle(
            "h3", fontName="Helvetica-Bold",
            fontSize=10, textColor=C_CYAN, leading=14,
            spaceBefore=8, spaceAfter=3),

        "body": ParagraphStyle(
            "body", fontName="Helvetica",
            fontSize=9, textColor=C_LIGHT, leading=15, spaceAfter=4),

        "bullet": ParagraphStyle(
            "bullet", fontName="Helvetica",
            fontSize=9, textColor=C_LIGHT, leading=14,
            spaceAfter=2, leftIndent=14, bulletIndent=4),

        "mono": ParagraphStyle(
            "mono", fontName="Courier",
            fontSize=8.5, textColor=C_LIGHT, leading=13, spaceAfter=2),

        "label": ParagraphStyle(
            "label", fontName="Helvetica-Bold",
            fontSize=7.5, textColor=C_SUB, leading=10, spaceAfter=2),

        "muted": ParagraphStyle(
            "muted", fontName="Helvetica",
            fontSize=8, textColor=C_MUTED, leading=12),

        "exec_body": ParagraphStyle(
            "exec_body", fontName="Helvetica",
            fontSize=10, textColor=C_WHITE, leading=17, spaceAfter=4),

        "score_bar": ParagraphStyle(
            "score_bar", fontName="Courier",
            fontSize=9, textColor=C_WHITE, leading=14, spaceAfter=1),
    }


# ── Flowable helpers ──────────────────────────────────────────────────────────
def thin_rule(color=C_BORDER):
    return HRFlowable(width="100%", thickness=1, color=color,
                      spaceAfter=8, spaceBefore=2)

def cyan_rule():
    return HRFlowable(width="100%", thickness=1.5, color=C_CYAN,
                      spaceAfter=8, spaceBefore=0)

def dark_table(data, col_widths, header_row=False):
    """Generic dark-themed table."""
    t = Table(data, colWidths=col_widths)
    style = [
        ("BACKGROUND",    (0, 0), (-1, -1), C_SURFACE),
        ("GRID",          (0, 0), (-1, -1), 0.5, C_BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 9),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 9),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if header_row:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), C_BG2),
            ("LINEBELOW",  (0, 0), (-1, 0), 1, C_BORDER),
        ]
    t.setStyle(TableStyle(style))
    return t

def strip_markdown(text):
    """Remove common markdown from text before PDF rendering."""
    import re
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)   # bold
    text = re.sub(r'\*(.+?)\*',   r'\1', text)   # italic
    text = re.sub(r'`(.+?)`',       r'\1', text)   # code
    text = re.sub(r'#+\s*',        '',     text)   # headings
    return text.strip()

def callout_box(text, styles):
    """
    Exec summary rendered as plain flowing paragraphs with a cyan left rule.
    Returns a LIST of flowables (not a table) so ReportLab can paginate freely.
    """
    clean = strip_markdown(text)
    # Take only first 3 sentences to keep it tight on the page
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean) if s.strip()]
    summary   = " ".join(sentences[:5])   # max 5 sentences
    safe      = summary.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    return Paragraph(safe, styles["exec_body"])

def score_bar_row(label, score, total, conf, styles):
    filled = int(round((score / total) * 12))
    bar = "█" * filled + "░" * (12 - filled)
    _, hex_col = score_color(score, total)
    row = [[
        Paragraph(label, styles["body"]),
        Paragraph(f'<font color="{hex_col}" name="Courier">{bar}</font>', styles["score_bar"]),
        Paragraph(f'<b><font color="{hex_col}">{score}/{total}</font></b>', styles["body"]),
        Paragraph(f'[{conf}]', styles["muted"]),
    ]]
    t = Table(row, colWidths=[2.1*inch, 1.9*inch, 0.6*inch, 0.4*inch])
    t.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND",    (0, 0), (-1, -1), C_SURFACE),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.5, C_BORDER),
    ]))
    return t

def overall_score_block(score, styles):
    if score >= 80:   label, hex_col, bg = "HEALTHY",          HEX_GREEN,  colors.HexColor("#0C2E1E")
    elif score >= 60: label, hex_col, bg = "NEEDS ATTENTION",  HEX_YELLOW, colors.HexColor("#2E230C")
    else:             label, hex_col, bg = "AT RISK",          HEX_RED,    colors.HexColor("#2E0C0C")

    data = [[
        Paragraph(
            f'<font color="{hex_col}"><b>OVERALL: {score}/100</b></font>',
            ParagraphStyle("os1", fontName="Helvetica-Bold", fontSize=18,
                           textColor=colors.HexColor(hex_col), alignment=TA_CENTER, leading=22)
        ),
        Paragraph(
            f'<font color="{hex_col}"><b>{label}</b></font>',
            ParagraphStyle("os2", fontName="Helvetica-Bold", fontSize=13,
                           textColor=colors.HexColor(hex_col), alignment=TA_CENTER, leading=18)
        ),
    ]]
    t = Table(data, colWidths=[3.0*inch, 2.0*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("BOX",           (0, 0), (-1, -1), 1.5, colors.HexColor(hex_col)),
        ("LINEAFTER",     (0, 0), (0, 0), 0.5, C_BORDER),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
    ]))
    return t


# ── Report parsers ────────────────────────────────────────────────────────────
def parse_overall(text):
    m = re.search(r'OVERALL[:\s]+(\d+)/100', text, re.IGNORECASE)
    return int(m.group(1)) if m else None

def parse_scores(text):
    results = []
    re_pat = re.compile(
        r'(\d+)\.\s+([\w /]+?)\s+[█░\s]+(\d+)/(\d+)\s+\[Confidence:\s*([HML])\]',
        re.IGNORECASE
    )
    for m in re_pat.finditer(text):
        results.append({
            "label": m.group(2).strip(),
            "score": int(m.group(3)),
            "total": int(m.group(4)),
            "conf":  m.group(5).upper(),
        })
    return results

def parse_section(text, heading):
    pat = re.compile(
        rf'{re.escape(heading)}\s*\n(.*?)(?=\n[A-Z][A-Z &/\-]+\n|\Z)',
        re.DOTALL | re.IGNORECASE
    )
    m = pat.search(text)
    return m.group(1).strip() if m else ""

def parse_exec(text):
    for h in ["EXECUTIVE SUMMARY", "Executive Summary"]:
        s = parse_section(text, h)
        if s: return s
    return ""

def parse_table_rows(text):
    rows = []
    lines = text.splitlines()
    in_table = False
    for line in lines:
        s = line.strip()
        if re.match(r'^\|.*Company.*Score', s, re.I): in_table = True; continue
        if re.match(r'^\|[-| :]+\|', s): continue
        if in_table and s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            rows.append(cells)
        elif in_table:
            break
    return rows


# ── PDF builder ───────────────────────────────────────────────────────────────
def sanitize_report(text):
    """Remove all table lines, markdown, and emojis from report text before parsing."""
    import re
    clean_lines = []
    emoji_pat = re.compile(
        u'[\U0001F300-\U0001F9FF\U00002600-\U000027BF'
        u'\U0001FA00-\U0001FA9F\U00002500-\U00002BEF'
        u'\U0000FE00-\U0000FE0F]+', re.UNICODE)
    for line in text.splitlines():
        s = line.strip()
        # Drop ALL lines with 2+ pipe chars (every table variant)
        if s.count('|') >= 2:
            continue
        # Drop horizontal rule lines
        if re.match(r'^[━═─\-]{4,}$', s):
            continue
        # Strip markdown
        s = re.sub(r'^#{1,6}\s*', '', s)
        s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
        s = re.sub(r'\*(.+?)\*', r'\1', s)
        s = re.sub(r'`(.+?)`', r'\1', s)
        s = emoji_pat.sub('', s).strip('#* ').strip()
        clean_lines.append(s)
    return '\n'.join(clean_lines)

def build_pdf(report_text, company, output_path):
    styles = build_styles()
    generated = datetime.now().strftime("%B %d, %Y  %H:%M")
    # Sanitize once — removes all tables, markdown, emojis before any parsing
    report_text = sanitize_report(report_text)

    # Two-pass: first pass counts pages
    # We use a custom doc class to store metadata for the page callback
    class DarkDoc(SimpleDocTemplate):
        pass

    doc = DarkDoc(
        output_path,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN + 0.7 * inch,
        bottomMargin=MARGIN + 0.55 * inch,
        allowSplitting=1,
        title=f"AI Stack Doctor v2 — {company}",
        author="AI Stack Doctor v2",
        subject="AI Infrastructure Health Report",
    )
    doc._company = company
    doc._generated = generated
    doc._page_count = 999  # placeholder; updated after first build

    story = []

    # ── COVER ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.9 * inch))

    # Title block (dark table so background shows correctly)
    title_data = [[Paragraph("AI STACK DOCTOR", styles["cover_title"])]]
    title_tbl = Table(title_data, colWidths=[INNER_W])
    title_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_BG2),
        ("TOPPADDING",    (0, 0), (-1, -1), 22),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW",     (0, 0), (-1, -1), 2, C_CYAN),
    ]))
    story.append(title_tbl)

    sub_data = [[Paragraph("AI INFRASTRUCTURE HEALTH REPORT", styles["cover_sub"])]]
    sub_tbl = Table(sub_data, colWidths=[INNER_W])
    sub_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_BG2),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 22),
    ]))
    story.append(sub_tbl)
    story.append(Spacer(1, 0.35 * inch))

    # Company name
    co_data = [[Paragraph(company.upper(), styles["cover_company"])]]
    co_tbl = Table(co_data, colWidths=[INNER_W])
    co_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_SURFACE),
        ("BOX",           (0, 0), (-1, -1), 1.5, C_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
    ]))
    story.append(co_tbl)
    story.append(Spacer(1, 0.4 * inch))

    # Overall score badge on cover
    overall = parse_overall(report_text)
    if overall is not None:
        story.append(overall_score_block(overall, styles))
        story.append(Spacer(1, 0.4 * inch))

    story.append(Paragraph(f"Generated: {generated}", styles["cover_meta"]))
    story.append(Paragraph("Powered by AI Stack Doctor v2  ·  Open Source", styles["cover_meta"]))
    story.append(PageBreak())

    # ── EXECUTIVE SUMMARY ────────────────────────────────────────────────────
    exec_text = parse_exec(report_text)
    if exec_text:
        story.append(Paragraph("EXECUTIVE SUMMARY", styles["h1"]))
        story.append(cyan_rule())
        # Render exec summary as plain flowing paragraphs — NO table wrapper
        # This lets ReportLab paginate freely regardless of length
        clean_exec = strip_markdown(exec_text)
        # Split on newlines and render each as its own paragraph
        exec_lines = [l.strip() for l in clean_exec.splitlines() if l.strip()]
        for line in exec_lines:
            safe_line = line.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            story.append(Paragraph(safe_line, styles["exec_body"]))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 0.2 * inch))

    # ── SCORE DASHBOARD ──────────────────────────────────────────────────────
    scores = parse_scores(report_text)
    if scores:
        story.append(Paragraph("CATEGORY SCORE DASHBOARD", styles["h1"]))
        story.append(cyan_rule())
        story.append(Paragraph(
            "HEALTH KEY   ■ 80-100 HEALTHY   ■ 60-79 NEEDS ATTENTION   ■ <60 AT RISK",
            styles["label"]
        ))
        story.append(Spacer(1, 8))

        items = []
        for s in scores:
            items.append(score_bar_row(s["label"], s["score"], s["total"], s["conf"], styles))
            items.append(Spacer(1, 2))
        if overall is not None:
            items.append(Spacer(1, 12))
            items.append(overall_score_block(overall, styles))
        story.append(KeepTogether(items))
        story.append(Spacer(1, 0.3 * inch))

    # ── PEER BENCHMARKING TABLE ──────────────────────────────────────────────
    peer_rows = parse_table_rows(report_text)
    if peer_rows:
        story.append(PageBreak())
        story.append(Paragraph("PEER BENCHMARKING", styles["h1"]))
        story.append(cyan_rule())

        headers = [
            Paragraph("<b>Company</b>", styles["label"]),
            Paragraph("<b>Score</b>", styles["label"]),
            Paragraph("<b>Strongest Area</b>", styles["label"]),
            Paragraph("<b>Weakest Area</b>", styles["label"]),
            Paragraph("<b>Maturity</b>", styles["label"]),
        ]
        col_ws = [1.4*inch, 0.7*inch, 1.5*inch, 1.5*inch, 1.1*inch]
        tbl_data = [headers]
        for row in peer_rows:
            while len(row) < 5: row.append("")
            tbl_data.append([Paragraph(c, styles["body"]) for c in row[:5]])

        peer_tbl = Table(tbl_data, colWidths=col_ws, repeatRows=1)
        peer_tbl.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0), C_BG2),
            ("BACKGROUND",     (0, 1), (-1, -1), C_SURFACE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_SURFACE, colors.HexColor("#0F1923")]),
            ("GRID",           (0, 0), (-1, -1), 0.5, C_BORDER),
            ("VALIGN",         (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",    (0, 0), (-1, -1), 9),
            ("RIGHTPADDING",   (0, 0), (-1, -1), 9),
            ("TOPPADDING",     (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 7),
        ]))
        story.append(peer_tbl)
        story.append(Spacer(1, 0.3 * inch))

    # ── FULL REPORT BODY ─────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("FULL REPORT", styles["h1"]))
    story.append(cyan_rule())

    skip_re = [
        re.compile(r'^[━═─]{4,}$'),
        re.compile(r'^🤖\s*AI STACK HEALTH REPORT', re.I),
        re.compile(r'^EXECUTIVE SUMMARY\s*$', re.I),
        re.compile(r'^CATEGORY SCORES?\s*$', re.I),
        re.compile(r'^\d+\.\s+[\w /]+[█░]+\s*\d+/\d+', re.I),
        re.compile(r'^OVERALL[:\s]+\d+/100', re.I),
        re.compile(r'^PEER BENCHMARKING\s*$', re.I),
        re.compile(r'^\|.*\|\s*$'),           # pipe table rows (any ending)
        re.compile(r'^\|[-| :─━]+\|\s*$'),    # pipe table separators
        re.compile(r'^\s*\|.*\|\s*$'),        # pipe rows with leading spaces
        re.compile(r'.*\|.*\|.*\|.*'),          # any line with 3+ pipe chars
        re.compile(r'^SCORE DELTA', re.I),        # delta section header
        re.compile(r'^Generated:', re.I),          # timestamp lines
        re.compile(r'^Mode:', re.I),               # mode line
    ]
    section_re = re.compile(r'^([A-Z][A-Z &/\-]{3,})$')
    bullet_re  = re.compile(r'^[\-\*•▸►]\s+(.+)')

    for line in report_text.splitlines():
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 4))
            continue
        if any(p.match(stripped) for p in skip_re):
            continue

        clean = re.sub(r'[🔁⚠️✅🟢🟡🔴▸►•\*#]', '', stripped).strip()

        if section_re.match(clean) and 4 < len(clean) < 60:
            story.append(Spacer(1, 4))
            story.append(Paragraph(clean, styles["h2"]))
            story.append(thin_rule())
            continue

        m = bullet_re.match(stripped)
        if m:
            safe = m.group(1).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            story.append(Paragraph(f"• {safe}", styles["bullet"]))
            continue

        if re.search(r'[█░]', stripped):
            story.append(Paragraph(stripped, styles["score_bar"]))
            continue

        clean = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped)
        clean = re.sub(r'\*(.+?)\*',   r'\1', clean)
        clean = re.sub(r'`(.+?)`',       r'\1', clean)
        safe  = clean.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        story.append(Paragraph(safe, styles["body"]))

    # ── BUILD (two passes for page count) ────────────────────────────────────
    from io import BytesIO
    import copy

    # Pass 1 — count pages
    buf = BytesIO()
    tmp = DarkDoc(buf, pagesize=letter,
                  leftMargin=MARGIN, rightMargin=MARGIN,
                  topMargin=MARGIN + 0.55*inch, bottomMargin=MARGIN + 0.35*inch)
    tmp._company = company
    tmp._generated = generated
    tmp._page_count = 999
    tmp.build(story[:], onFirstPage=draw_page_background, onLaterPages=draw_page_background)
    page_count = tmp.page

    # Pass 2 — real build with correct page count
    doc._page_count = page_count
    doc.build(story, onFirstPage=draw_page_background, onLaterPages=draw_page_background)
    return output_path


# ── Public API ────────────────────────────────────────────────────────────────
def export_report_to_pdf(report_text, company, output_dir="."):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r'[^\w\-]', '_', company.lower())
    path = os.path.join(output_dir, f"ai_stack_report_{safe}_{timestamp}.pdf")
    build_pdf(report_text, company, path)
    return os.path.abspath(path)


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Stack Doctor v2 — PDF Exporter")
    parser.add_argument("--input",   required=True)
    parser.add_argument("--output",  default=None)
    parser.add_argument("--company", default="")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: '{args.input}' not found."); sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()

    company = args.company or os.path.basename(args.input).replace("_"," ").replace(".txt","")
    out = args.output or export_report_to_pdf(text, company)
    if args.output:
        build_pdf(text, company, args.output)
        out = args.output
    print(f"\n✓ PDF exported to: {out}\n")
