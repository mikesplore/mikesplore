#!/usr/bin/env python3
"""
Render cv_data.json into a clean, ATS-friendly PDF.

Usage:
    python3 render_cv.py [cv_data.json] [output.pdf]

This script is intentionally dumb: it does zero content editing.
The bot that tailors the CV to a job description should only ever
write to cv_data.json (validated against the same schema shown in
this file's expected keys). This script just lays it out.
"""

import json
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem,
    KeepTogether
)

ACCENT = colors.HexColor("#1a1a1a")
MUTED = colors.HexColor("#555555")


def without_em_dashes(value):
    """Normalize all CV text before it reaches the PDF layout."""
    if isinstance(value, str):
        return value.replace("—", "-").replace("–", "-")
    if isinstance(value, list):
        return [without_em_dashes(item) for item in value]
    if isinstance(value, dict):
        return {key: without_em_dashes(item) for key, item in value.items()}
    return value


def build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "CVName", parent=styles["Title"], fontSize=18, leading=22,
        alignment=TA_CENTER, spaceAfter=2, textColor=ACCENT,
    ))
    styles.add(ParagraphStyle(
        "CVTitle", parent=styles["Normal"], fontSize=10.5, leading=13,
        alignment=TA_CENTER, textColor=MUTED, spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        "CVContact", parent=styles["Normal"], fontSize=9, leading=12,
        alignment=TA_CENTER, textColor=MUTED, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        "SectionHeader", parent=styles["Heading2"], fontSize=11.5,
        leading=14, spaceBefore=9, spaceAfter=3, textColor=ACCENT,
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=9.5, leading=13,
        textColor=colors.HexColor("#222222"),
    ))
    styles.add(ParagraphStyle(
        "ProjectTitle", parent=styles["Normal"], fontSize=10, leading=13,
        fontName="Helvetica-Bold", textColor=ACCENT,
    ))
    styles.add(ParagraphStyle(
        "ProjectMeta", parent=styles["Normal"], fontSize=8.5, leading=11,
        textColor=MUTED, spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        "BulletText", parent=styles["Normal"], fontSize=9.3, leading=12.5,
        textColor=colors.HexColor("#222222"),
    ))
    return styles


def section_header(text, styles, story, glue=None):
    header = Paragraph(text.upper(), styles["SectionHeader"])
    rule = HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cccccc"), spaceAfter=6)
    if glue is not None:
        group = glue if isinstance(glue, list) else [glue]
        story.append(KeepTogether([header, rule] + group))
    else:
        story.append(header)
        story.append(rule)


def bullets(items, styles):
    return ListFlowable(
        [ListItem(Paragraph(b, styles["BulletText"]), leftIndent=8, bulletIndent=0) for b in items],
        bulletType="bullet", start="•", leftIndent=14, spaceAfter=4,
    )


def render(data, out_path):
    data = without_em_dashes(data)
    styles = build_styles()
    doc = SimpleDocTemplate(
        out_path, pagesize=letter,
        leftMargin=0.65 * inch, rightMargin=0.65 * inch,
        topMargin=0.45 * inch, bottomMargin=0.45 * inch,
    )
    story = []

    # Header
    story.append(Paragraph(data["name"], styles["CVName"]))
    story.append(Paragraph(data["title"], styles["CVTitle"]))
    c = data["contact"]
    parts = [c.get("location"), c.get("email"), c.get("phone")]
    if c.get("email"):
        parts[1] = f'<link href="mailto:{c["email"]}" color="#555555">{c["email"]}</link>'
    for key in ("website", "github"):
        if c.get(key):
            url = c[key] if c[key].startswith("http") else f'https://{c[key]}'
            parts.append(f'<link href="{url}" color="#555555">{c[key]}</link>')
    contact_line = " | ".join(filter(None, parts))
    story.append(Paragraph(contact_line, styles["CVContact"]))

    ai = data.get("additional_info", {})
    footnote = " &nbsp;|&nbsp; ".join(b for b in (ai.get("languages"), ai.get("work_style")) if b)
    if footnote:
        story.append(Paragraph(footnote, styles["CVContact"]))

    # Summary
    section_header("Summary", styles, story, Paragraph(data["summary"], styles["Body"]))

    # Skills
    skill_paras = [Paragraph(f"<b>{g['category']}:</b> " + ", ".join(g["items"]), styles["Body"]) for g in data["skills"]]
    section_header("Technical Skills", styles, story, skill_paras[0] if skill_paras else None)
    for para in skill_paras[1:]:
        story.append(Spacer(1, 2))
        story.append(para)

    # Projects
    section_header("Key Projects", styles, story)
    for p in data["projects"]:
        story.append(Paragraph(f"{p['name']}  <font color='#555555'>- {p['date']}</font>", styles["ProjectTitle"]))
        story.append(Paragraph(p["stack"], styles["ProjectMeta"]))
        story.append(bullets(p["bullets"], styles))

    # Certifications
    section_header("Certifications & Competitions", styles, story)
    story.append(bullets(data["certifications"], styles))

    # Education
    section_header("Education", styles, story)
    for e in data["education"]:
        story.append(Paragraph(f"<b>{e['institution']}</b>", styles["Body"]))
        story.append(Paragraph(e["degree"], styles["Body"]))
        story.append(Spacer(1, 4))

    # Additional info
    ai = data.get("additional_info", {})
    if ai:
        section_header("Additional Information", styles, story)
        for label, val in [
            ("Work style", ai.get("work_style")),
            ("Languages", ai.get("languages")),
            ("Location", ai.get("location_note")),
        ]:
            if val:
                story.append(Paragraph(f"<b>{label}:</b> {val}", styles["Body"]))

    doc.build(story)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "cv_data.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "cv_output.pdf"
    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)
    render(data, out)
    print(f"Rendered {out}")
