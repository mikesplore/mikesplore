#!/usr/bin/env python3
"""
Render verified portfolio-derived CV data into a clean, ATS-friendly PDF.

Usage:
    python3 render_cv.py [cv_data.json] [output.pdf]

This script is intentionally dumb: it does zero content editing.
The backend maps current portfolio records into the renderer's data shape;
this script only lays them out.
"""

import json
import sys
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether
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
    if not items:
        return []
    bullet_style = ParagraphStyle(
        "InlineBulletText", parent=styles["BulletText"], leftIndent=12,
        firstLineIndent=-10, spaceAfter=2,
    )
    return [Paragraph(f"•&nbsp;&nbsp;{item}", bullet_style) for item in items]


def render(data, out_path):
    data = without_em_dashes(data)
    def esc(value):
        return escape(str(value or ""))
    styles = build_styles()
    doc = SimpleDocTemplate(
        out_path, pagesize=letter,
        leftMargin=0.65 * inch, rightMargin=0.65 * inch,
        topMargin=0.45 * inch, bottomMargin=0.45 * inch,
    )
    story = []

    # Header
    story.append(Paragraph(esc(data["name"]), styles["CVName"]))
    if data.get("title"):
        story.append(Paragraph(esc(data["title"]), styles["CVTitle"]))
    c = data["contact"]
    parts = [esc(c.get("location")), esc(c.get("email")), esc(c.get("phone"))]
    if c.get("email"):
        email = esc(c["email"])
        parts[1] = f'<link href="mailto:{email}" color="#555555">{email}</link>'
    for key in ("website", "github"):
        if c.get(key):
            display = esc(c[key])
            url = escape(c[key] if c[key].startswith("http") else f'https://{c[key]}', {'"': '&quot;'})
            parts.append(f'<link href="{url}" color="#555555">{display}</link>')
    contact_line = " | ".join(filter(None, parts))
    profile_links = (data.get("profiles") or [])[:5]
    if profile_links:
        rendered_profiles = []
        for profile in profile_links:
            name = esc(profile.get("name"))
            raw_url = str(profile.get("url") or "").strip()
            if name and raw_url.startswith(("http://", "https://")):
                url = escape(raw_url, {'"': '&quot;'})
                rendered_profiles.append(f'<link href="{url}" color="#555555">{name}</link>')
        if rendered_profiles:
            contact_line = " | ".join(filter(None, (contact_line, " · ".join(rendered_profiles))))
    if contact_line:
        story.append(Paragraph(contact_line, styles["CVContact"]))

    ai = data.get("additional_info", {})

    # Summary
    if data.get("summary"):
        section_header("Summary", styles, story, Paragraph(esc(data["summary"]), styles["Body"]))

    # Skills
    skill_paras = [Paragraph(f"<b>{esc(g['category'])}:</b> " + ", ".join(esc(item) for item in g["items"]), styles["Body"]) for g in data["skills"]]
    if skill_paras:
        section_header("Technical Skills", styles, story, skill_paras[0])
        for para in skill_paras[1:]:
            story.append(Spacer(1, 2))
            story.append(para)

    # Projects
    if data["projects"]:
        section_header("Key Projects", styles, story)
        for p in data["projects"]:
            date_label = f"  <font color='#555555'>- {esc(p['date'])}</font>" if p.get("date") else ""
            story.append(Paragraph(f"{esc(p['name'])}{date_label}", styles["ProjectTitle"]))
            if p.get("stack"):
                story.append(Paragraph(esc(p["stack"]), styles["ProjectMeta"]))
            story.extend(bullets([esc(item) for item in p["bullets"][:3]], styles))

    # Certifications
    if data["certifications"]:
        section_header("Certifications & Competitions", styles, story)
        story.extend(bullets([esc(item) for item in data["certifications"]], styles))

    # Education
    if data["education"]:
        section_header("Education", styles, story)
        for e in data["education"]:
            story.append(Paragraph(f"<b>{esc(e['institution'])}</b>", styles["Body"]))
            story.append(Paragraph(esc(e["degree"]), styles["Body"]))
            story.append(Spacer(1, 4))

    # Additional info
    ai = data.get("additional_info", {})
    skills_have_languages = any("language" in str(group.get("category", "")).lower() for group in data.get("skills", []))
    has_contact_location = bool(c.get("location"))
    additional_rows = [
        ("Work style", ai.get("work_style")),
        ("Languages", None if skills_have_languages else ai.get("languages")),
        ("Location", None if has_contact_location else ai.get("location_note")),
    ]
    if any(value for _label, value in additional_rows):
        section_header("Additional Information", styles, story)
        for label, val in additional_rows:
            if val:
                story.append(Paragraph(f"<b>{label}:</b> {esc(val)}", styles["Body"]))

    doc.build(story)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "cv_data.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "cv_output.pdf"
    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)
    render(data, out)
    print(f"Rendered {out}")
