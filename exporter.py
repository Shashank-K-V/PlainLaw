from io import BytesIO
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
)

from models import AnalyzedClause, DocumentSummary
from parser import extract_clause_title


# ── Colours ────────────────────────────────────────────────────────────────────

RED    = colors.HexColor("#c0392b")
AMBER  = colors.HexColor("#e8a020")
GREEN  = colors.HexColor("#1d9e75")
LIGHT_RED   = colors.HexColor("#fbeaea")
LIGHT_AMBER = colors.HexColor("#fdf3e3")
LIGHT_GREEN = colors.HexColor("#e6f4f0")
INK    = colors.HexColor("#0f0e0c")
INK2   = colors.HexColor("#3a3831")
PAPER  = colors.HexColor("#f7f4ef")
BORDER = colors.HexColor("#e3dfd6")

RISK_COLOR  = {"high": RED,    "medium": AMBER,  "low": GREEN}
RISK_BG     = {"high": LIGHT_RED, "medium": LIGHT_AMBER, "low": LIGHT_GREEN}
RISK_LABEL  = {"high": "HIGH RISK", "medium": "REVIEW CAREFULLY", "low": "STANDARD"}


# ── Styles ─────────────────────────────────────────────────────────────────────

def _build_styles():
    base = getSampleStyleSheet()

    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        "title": S("PL-Title", fontSize=22, fontName="Helvetica-Bold",
                   textColor=INK, spaceAfter=4, leading=26),
        "subtitle": S("PL-Sub", fontSize=10, fontName="Helvetica",
                      textColor=INK2, spaceAfter=2),
        "section": S("PL-Section", fontSize=8, fontName="Helvetica-Bold",
                     textColor=colors.HexColor("#7a7670"),
                     spaceBefore=18, spaceAfter=6,
                     borderPadding=(0, 0, 4, 0)),
        "clause_title": S("PL-ClauseTitle", fontSize=11, fontName="Helvetica-Bold",
                          textColor=INK, spaceBefore=0, spaceAfter=3),
        "body": S("PL-Body", fontSize=9, fontName="Helvetica",
                  textColor=INK2, leading=14, spaceAfter=4),
        "small": S("PL-Small", fontSize=8, fontName="Helvetica",
                   textColor=INK2, leading=12),
        "label": S("PL-Label", fontSize=7, fontName="Helvetica-Bold",
                   textColor=colors.HexColor("#7a7670"),
                   spaceBefore=6, spaceAfter=2),
        "risk_text": S("PL-Risk", fontSize=9, fontName="Helvetica",
                       textColor=INK2, leading=13),
        "disclaimer": S("PL-Disc", fontSize=7, fontName="Helvetica-Oblique",
                        textColor=colors.HexColor("#9a9690"),
                        spaceBefore=16, spaceAfter=0, alignment=TA_CENTER),
    }


# ── Risk badge table cell ─────────────────────────────────────────────────────

def _risk_badge(level: str, styles: dict):
    label = RISK_LABEL.get(level, level.upper())
    color = RISK_COLOR.get(level, INK2)
    bg    = RISK_BG.get(level, PAPER)
    p = Paragraph(f'<font color="{color.hexval()}" size="7"><b>{label}</b></font>',
                  styles["small"])
    t = Table([[p]], colWidths=[3.2 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX",        (0, 0), (-1, -1), 0.5, color),
        ("ROUNDEDCORNERS", [4]),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ]))
    return t


# ── Main builder ──────────────────────────────────────────────────────────────

def build_pdf_report(
    analyzed: list[AnalyzedClause],
    summary: DocumentSummary | None,
    filename: str = "contract",
) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        topMargin=2 * cm,    bottomMargin=2 * cm,
        title="Viveka Report",
    )

    styles = _build_styles()
    story = []
    W = A4[0] - 4.4 * cm  # usable width

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("Viveka", styles["title"]))
    story.append(Paragraph(
        f"Contract analysis report  ·  {filename}  ·  {date.today().strftime('%d %b %Y')}",
        styles["subtitle"],
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=10))

    # ── Risk summary bar ──────────────────────────────────────────────────────
    counts = {"high": 0, "medium": 0, "low": 0}
    for a in analyzed:
        if a.analysis:
            counts[a.analysis.risk_level] = counts.get(a.analysis.risk_level, 0) + 1

    def _count_cell(label, n, color, bg):
        inner = Table([
            [Paragraph(f'<font color="{color.hexval()}" size="8"><b>{n}</b></font>', styles["body"])],
            [Paragraph(f'<font color="{color.hexval()}" size="7">{label}</font>', styles["small"])],
        ], colWidths=[W / 3 - 0.3 * cm])
        inner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("BOX", (0, 0), (-1, -1), 0.5, color),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return inner

    bar = Table([[
        _count_cell("High Risk",        counts["high"],   RED,   LIGHT_RED),
        _count_cell("Review Carefully", counts["medium"], AMBER, LIGHT_AMBER),
        _count_cell("Standard",         counts["low"],    GREEN, LIGHT_GREEN),
    ]], colWidths=[W / 3] * 3, hAlign="LEFT")
    bar.setStyle(TableStyle([("LEFTPADDING", (0,0),(-1,-1), 4), ("RIGHTPADDING", (0,0),(-1,-1), 4)]))
    story.append(bar)
    story.append(Spacer(1, 0.5 * cm))

    # ── Document summary ──────────────────────────────────────────────────────
    if summary:
        story.append(Paragraph("DOCUMENT SUMMARY", styles["section"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6))
        story.append(Paragraph(f"<b>{summary.contract_type}</b>", styles["clause_title"]))
        story.append(Paragraph(summary.one_liner, styles["body"]))

        if summary.top_risks:
            story.append(Paragraph("TOP RISKS", styles["label"]))
            for r in summary.top_risks:
                story.append(Paragraph(f"• {r}", styles["body"]))

        if summary.lawyer_questions:
            story.append(Paragraph("QUESTIONS TO ASK BEFORE SIGNING", styles["label"]))
            for q in summary.lawyer_questions:
                story.append(Paragraph(f"• {q}", styles["body"]))

        story.append(Spacer(1, 0.4 * cm))

    # ── Clause-by-clause ─────────────────────────────────────────────────────
    story.append(Paragraph("CLAUSE ANALYSIS", styles["section"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=8))

    # Sort high → medium → low
    ordered = sorted(
        analyzed,
        key=lambda a: {"high": 0, "medium": 1, "low": 2}.get(
            a.analysis.risk_level if a.analysis else "low", 3
        ),
    )

    for ac in ordered:
        if not ac.analysis:
            continue
        level = ac.analysis.risk_level
        bg    = RISK_BG[level]
        border_color = RISK_COLOR[level]

        title = extract_clause_title(ac.text) or f"Clause {ac.index + 1}"

        # Build inner content
        inner_rows = []

        # Title + badge row
        title_p = Paragraph(f"<b>{title}</b>", styles["clause_title"])
        badge   = _risk_badge(level, styles)
        inner_rows.append(Table(
            [[title_p, badge]],
            colWidths=[W - 4 * cm - 0.6 * cm, 3.2 * cm],
            hAlign="LEFT",
        ))

        # Plain English
        inner_rows.append(Spacer(1, 4))
        inner_rows.append(Paragraph("<b>Plain English</b>", styles["label"]))
        inner_rows.append(Paragraph(ac.analysis.plain_english, styles["risk_text"]))

        # Why it matters
        inner_rows.append(Paragraph("<b>Why it matters</b>", styles["label"]))
        inner_rows.append(Paragraph(ac.analysis.risk_reason, styles["risk_text"]))

        # Tags
        if ac.analysis.tags:
            tags_str = "  ·  ".join(ac.analysis.tags)
            inner_rows.append(Paragraph("<b>Tags</b>", styles["label"]))
            inner_rows.append(Paragraph(tags_str, styles["small"]))

        # Questions
        if ac.analysis.questions:
            inner_rows.append(Paragraph("<b>Questions to ask</b>", styles["label"]))
            for q in ac.analysis.questions:
                inner_rows.append(Paragraph(f"• {q}", styles["small"]))

        # Wrap in a colored box
        cell_table = Table([[row] for row in inner_rows], colWidths=[W - 0.6 * cm])
        cell_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), bg),
            ("BOX",           (0, 0), (-1, -1), 0.8, border_color),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
            ("TOPPADDING",    (0, 0), (0, 0),   10),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
        ]))
        story.append(cell_table)
        story.append(Spacer(1, 0.25 * cm))

    # ── Disclaimer ────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceBefore=12))
    story.append(Paragraph(
        "Generated by Viveka · This report is for informational purposes only and does not constitute legal advice. "
        "Consult a qualified lawyer before signing any contract.",
        styles["disclaimer"],
    ))

    doc.build(story)
    return buf.getvalue()
