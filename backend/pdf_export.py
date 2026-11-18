"""
PDF Export.
==============
Builds a clean, professional single-page-flow PDF from a meeting record.
Uses reportlab (Platypus), which needs no system dependencies beyond the
pip package — good for a Flask app end users will run locally.
"""

import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, HRFlowable
)

ACCENT = colors.HexColor("#C87F1F")
ACTION = colors.HexColor("#3E6BAE")
DECISION = colors.HexColor("#3C8C5C")
DEADLINE = colors.HexColor("#B4463C")
TEXT_DARK = colors.HexColor("#1c212c")
TEXT_MUTED = colors.HexColor("#6b7280")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("TitleX", parent=base["Title"], fontSize=22,
                                 textColor=TEXT_DARK, spaceAfter=4),
        "meta": ParagraphStyle("Meta", parent=base["Normal"], fontSize=10,
                                textColor=TEXT_MUTED, spaceAfter=18),
        "heading": ParagraphStyle("HeadingX", parent=base["Heading2"], fontSize=13,
                                   spaceBefore=16, spaceAfter=8),
        "body": ParagraphStyle("BodyX", parent=base["Normal"], fontSize=11,
                                leading=16, textColor=TEXT_DARK),
        "item": ParagraphStyle("ItemX", parent=base["Normal"], fontSize=10.5,
                                leading=15, textColor=TEXT_DARK),
        "empty": ParagraphStyle("EmptyX", parent=base["Normal"], fontSize=10.5,
                                 textColor=TEXT_MUTED, fontName="Helvetica-Oblique"),
    }


def _section(story, styles, heading, color, items, is_summary=False):
    story.append(Paragraph(heading, ParagraphStyle(
        "H", parent=styles["heading"], textColor=color)))
    story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#e5e7eb"),
                             spaceAfter=8))

    if is_summary:
        if items:
            for line in items:
                story.append(Paragraph(line, styles["body"]))
        else:
            story.append(Paragraph("None", styles["empty"]))
        return

    if items and items not in (["None"], ["no clear action items found."]):
        bullets = [ListItem(Paragraph(i, styles["item"]), bulletColor=color) for i in items]
        story.append(ListFlowable(bullets, bulletType="bullet", start="circle",
                                   leftIndent=14, bulletFontSize=6))
    else:
        story.append(Paragraph("None", styles["empty"]))


def generate_pdf(meeting: dict) -> io.BytesIO:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=0.85 * inch, bottomMargin=0.85 * inch,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
    )
    styles = _styles()
    story = []

    story.append(Paragraph(meeting["title"], styles["title"]))
    story.append(Paragraph(
        f"{meeting['created_at']} &nbsp;·&nbsp; {meeting['input_type'].capitalize()} input",
        styles["meta"],
    ))

    _section(story, styles, "Summary", ACCENT, meeting["summary"], is_summary=True)
    story.append(Spacer(1, 6))
    _section(story, styles, "Action Items", ACTION, meeting["action_items"])
    story.append(Spacer(1, 6))
    _section(story, styles, "Decisions", DECISION, meeting["decisions"])
    story.append(Spacer(1, 6))
    _section(story, styles, "Deadlines", DEADLINE, meeting["deadlines"])

    doc.build(story)
    buf.seek(0)
    return buf
