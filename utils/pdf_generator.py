"""
PDF report generator using ReportLab.
Produces a branded multi-page visibility report.
"""

from __future__ import annotations

from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Brand colours ──────────────────────────────────────────────────────────────
NAVY      = colors.HexColor("#0D1B2A")
BLUE      = colors.HexColor("#1565C0")
CYAN      = colors.HexColor("#00B4D8")
GREEN     = colors.HexColor("#2ECC71")
YELLOW    = colors.HexColor("#F39C12")
RED       = colors.HexColor("#E74C3C")
LIGHT_BG  = colors.HexColor("#F5F7FA")
MID_GREY  = colors.HexColor("#8E9AAB")
WHITE     = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 2 * cm


def _score_colour(score: float, max_score: float) -> colors.Color:
    pct = score / max_score if max_score else 0
    if pct >= 0.7:
        return GREEN
    if pct >= 0.4:
        return YELLOW
    return RED


def _grade_colour(grade: str) -> colors.Color:
    return {"A": GREEN, "B": CYAN, "C": YELLOW, "D": colors.HexColor("#FF7043"), "F": RED}.get(
        grade, MID_GREY
    )


def _make_styles():
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "title",
            fontSize=26,
            leading=32,
            textColor=WHITE,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#B0BEC5"),
            fontName="Helvetica",
            alignment=TA_CENTER,
        ),
        "section_heading": ParagraphStyle(
            "section_heading",
            fontSize=14,
            leading=20,
            textColor=NAVY,
            fontName="Helvetica-Bold",
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body",
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#333333"),
            fontName="Helvetica",
        ),
        "body_centre": ParagraphStyle(
            "body_centre",
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#333333"),
            fontName="Helvetica",
            alignment=TA_CENTER,
        ),
        "score_big": ParagraphStyle(
            "score_big",
            fontSize=72,
            leading=80,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
        "score_label": ParagraphStyle(
            "score_label",
            fontSize=12,
            leading=16,
            fontName="Helvetica",
            textColor=MID_GREY,
            alignment=TA_CENTER,
        ),
        "recommendation": ParagraphStyle(
            "recommendation",
            fontSize=10,
            leading=16,
            fontName="Helvetica",
            textColor=colors.HexColor("#333333"),
            leftIndent=14,
            spaceAfter=8,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontSize=8,
            leading=12,
            textColor=MID_GREY,
            fontName="Helvetica",
            alignment=TA_CENTER,
        ),
    }
    return styles


# ── Header / Footer canvas callbacks ──────────────────────────────────────────

def _header_footer(canvas, doc):
    canvas.saveState()
    w, h = doc.pagesize

    # Top bar
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 1.2 * cm, w, 1.2 * cm, fill=1, stroke=0)
    canvas.setFillColor(CYAN)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(MARGIN, h - 0.85 * cm, "LOCAL VISIBILITY REPORT")
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(w - MARGIN, h - 0.85 * cm, f"Generated {date.today().strftime('%B %d, %Y')}")

    # Bottom bar
    canvas.setFillColor(LIGHT_BG)
    canvas.rect(0, 0, w, 1.1 * cm, fill=1, stroke=0)
    canvas.setFillColor(MID_GREY)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(w / 2, 0.4 * cm, "Confidential | Local Visibility Report | Page %d" % doc.page)

    canvas.restoreState()


# ── Individual sections ────────────────────────────────────────────────────────

def _cover_section(styles, business: dict, scores: dict) -> list:
    elements = []

    # Dark header block
    score_colour = _grade_colour(scores["grade"])

    elements.append(Spacer(1, 1.5 * cm))

    # Big score circle (simulated with a coloured table cell)
    score_table = Table(
        [[Paragraph(str(scores["total"]), styles["score_big"])]],
        colWidths=[6 * cm],
        rowHeights=[6 * cm],
    )
    score_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), score_colour),
        ("ROUNDEDCORNERS", [50]),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TEXTCOLOR",     (0, 0), (-1, -1), WHITE),
    ]))

    wrapper = Table([[score_table]], colWidths=[PAGE_W - 2 * MARGIN])
    wrapper.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    elements.append(wrapper)

    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph("out of 100", styles["score_label"]))
    elements.append(Spacer(1, 0.15 * cm))
    elements.append(
        Paragraph(f'Grade: <b>{scores["grade"]}</b>', styles["body_centre"])
    )

    elements.append(Spacer(1, 0.8 * cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#DEE2E6")))
    elements.append(Spacer(1, 0.5 * cm))

    # Business info
    info_data = [
        ["Business", business["name"]],
        ["Address",  business.get("formatted_address", "—")],
        ["Rating",   f"{business.get('rating', 'N/A')} ★  ({business.get('review_count', 0):,} reviews)"],
        ["Report date", date.today().strftime("%B %d, %Y")],
    ]
    info_table = Table(info_data, colWidths=[4 * cm, PAGE_W - 2 * MARGIN - 4 * cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",    (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",   (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR",   (1, 0), (1, -1), colors.HexColor("#333333")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("LINEBELOW",   (0, 0), (-1, -2), 0.5, colors.HexColor("#DEE2E6")),
    ]))
    elements.append(info_table)

    return elements


def _score_breakdown_section(styles, scores: dict) -> list:
    elements = [PageBreak()]
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("Score Breakdown", styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=2, color=CYAN))
    elements.append(Spacer(1, 0.4 * cm))

    metrics = [
        ("Rating",                   "rating_score",       25, "Based on your Google star rating"),
        ("Reviews vs. Local Average","reviews_score",       25, "Your review count vs. top 5 local competitors"),
        ("Photo Count",              "photos_score",        20, "Number of photos on your Google Business Profile"),
        ("Business Categories",      "categories_score",    15, "Number of relevant categories listed"),
        ("Business Description",     "description_score",   10, "Google editorial summary / business description"),
        ("Review Response Rate",     "response_score",       5, "Percentage of reviews you've responded to"),
    ]

    header = [
        Paragraph("<b>Metric</b>", styles["body"]),
        Paragraph("<b>Score</b>", styles["body"]),
        Paragraph("<b>Max</b>", styles["body"]),
        Paragraph("<b>Visual</b>", styles["body"]),
        Paragraph("<b>Notes</b>", styles["body"]),
    ]
    rows = [header]

    for label, key, max_pts, note in metrics:
        pts = scores.get(key, 0)
        pct = pts / max_pts if max_pts else 0
        bar_filled = int(pct * 20)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        col = _score_colour(pts, max_pts)

        rows.append([
            Paragraph(label, styles["body"]),
            Paragraph(f"<b>{pts}</b>", ParagraphStyle("sc", parent=styles["body"], textColor=col, fontName="Helvetica-Bold")),
            Paragraph(str(max_pts), styles["body"]),
            Paragraph(f'<font color="#{col.hexval()[2:]}"><b>{bar}</b></font>', styles["body"]),
            Paragraph(note, ParagraphStyle("note", parent=styles["body"], textColor=MID_GREY, fontSize=8)),
        ])

    col_widths = [4.5 * cm, 1.5 * cm, 1.2 * cm, 4.5 * cm, 5.3 * cm]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#DEE2E6")),
        ("ALIGN",         (1, 0), (2, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)

    # Total row
    total_colour = _grade_colour(scores["grade"])
    elements.append(Spacer(1, 0.4 * cm))
    total_table = Table(
        [[
            Paragraph("<b>TOTAL VISIBILITY SCORE</b>", styles["body"]),
            Paragraph(
                f'<b>{scores["total"]} / 100</b>',
                ParagraphStyle("tot", parent=styles["body"], textColor=WHITE, fontName="Helvetica-Bold", fontSize=12),
            ),
        ]],
        colWidths=[PAGE_W - 2 * MARGIN - 4 * cm, 4 * cm],
    )
    total_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), total_colour),
        ("TEXTCOLOR",     (0, 0), (-1, -1), WHITE),
        ("ALIGN",         (1, 0), (1, 0), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", [4]),
    ]))
    elements.append(total_table)

    return elements


def _competitor_section(styles, business: dict, competitors: list[dict], scores: dict) -> list:
    elements = [PageBreak()]
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("Local Competitor Comparison", styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=2, color=CYAN))
    elements.append(Spacer(1, 0.4 * cm))
    elements.append(
        Paragraph(
            "How your Google Business Profile stacks up against your top local competitors:",
            styles["body"],
        )
    )
    elements.append(Spacer(1, 0.3 * cm))

    from utils.scoring import calculate_score as calc  # local import to avoid circular

    header = [
        Paragraph("<b>Business</b>", styles["body"]),
        Paragraph("<b>Rating</b>", styles["body"]),
        Paragraph("<b>Reviews</b>", styles["body"]),
        Paragraph("<b>Photos</b>", styles["body"]),
        Paragraph("<b>Description</b>", styles["body"]),
        Paragraph("<b>Score</b>", styles["body"]),
    ]
    rows = [header]

    # Your business row first
    your_score = scores["total"]
    your_col = _grade_colour(scores["grade"])

    def _row(profile, score_val, is_you=False):
        name = profile["name"]
        if is_you:
            name = f"{name} ★ YOU"
        return [
            Paragraph(name, ParagraphStyle(
                "rn", parent=styles["body"],
                fontName="Helvetica-Bold" if is_you else "Helvetica",
                textColor=BLUE if is_you else colors.HexColor("#333333"),
            )),
            Paragraph(f'{profile.get("rating", "—")} ★', styles["body"]),
            Paragraph(f'{profile.get("review_count", 0):,}', styles["body"]),
            Paragraph(str(profile.get("photo_count", 0)), styles["body"]),
            Paragraph("Yes" if profile.get("has_description") else "No", styles["body"]),
            Paragraph(
                f"<b>{score_val}</b>",
                ParagraphStyle("rs", parent=styles["body"],
                               textColor=_grade_colour(
                                   {v: k for k, v in {"A": 85, "B": 70, "C": 55, "D": 40}.items()
                                    }.get(str(score_val), "F")
                               ) if False else colors.HexColor("#333333"),
                               fontName="Helvetica-Bold"),
            ),
        ]

    rows.append(_row(business, your_score, is_you=True))

    for comp in competitors:
        comp_scores = calc(comp, [])
        rows.append(_row(comp, comp_scores["total"]))

    col_widths = [5.5 * cm, 2 * cm, 2.2 * cm, 1.8 * cm, 2.5 * cm, 2 * cm]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",      (0, 0), (-1, 0), WHITE),
        ("BACKGROUND",     (0, 1), (-1, 1), colors.HexColor("#E3F2FD")),
        ("ROWBACKGROUNDS", (0, 2), (-1, -1), [WHITE, LIGHT_BG]),
        ("GRID",           (0, 0), (-1, -1), 0.5, colors.HexColor("#DEE2E6")),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",     (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 7),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)

    return elements


def _recommendations_section(styles, scores: dict) -> list:
    elements = [PageBreak()]
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("Recommendations to Improve Your Score", styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=2, color=CYAN))
    elements.append(Spacer(1, 0.4 * cm))
    elements.append(
        Paragraph(
            "Based on your current Google Business Profile performance, here are the highest-impact "
            "actions you can take to improve your local visibility:",
            styles["body"],
        )
    )
    elements.append(Spacer(1, 0.35 * cm))

    for i, tip in enumerate(scores.get("recommendations", []), 1):
        elements.append(
            Paragraph(
                f"<b>{i}.</b>  {tip}",
                styles["recommendation"],
            )
        )

    elements.append(Spacer(1, 1 * cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#DEE2E6")))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(
        Paragraph(
            "<b>Want expert help implementing these improvements?</b>",
            styles["section_heading"],
        )
    )
    elements.append(
        Paragraph(
            "Our team specialises in local SEO and Google Business Profile optimisation. "
            "Book a free strategy call and let us help you dominate local search results.",
            styles["body"],
        )
    )

    return elements


# ── Main entry point ───────────────────────────────────────────────────────────

def _build_story(first_name: str, business: dict, scores: dict, competitors: list[dict]) -> list:
    styles = _make_styles()
    story = []
    story += _cover_section(styles, business, scores)
    story += _score_breakdown_section(styles, scores)
    story += _competitor_section(styles, business, competitors, scores)
    story += _recommendations_section(styles, scores)
    return story


def generate_pdf_bytes(
    first_name: str,
    business: dict,
    scores: dict,
    competitors: list[dict],
) -> bytes:
    """
    Generate a PDF report entirely in memory and return the raw bytes.
    No filesystem writes — safe for ephemeral hosting (Railway, Render, etc.).
    """
    import io as _io
    buf = _io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=1.8 * cm,
        bottomMargin=1.4 * cm,
        title=f"Local Visibility Report — {business['name']}",
        author="Local Visibility Tool",
    )
    doc.build(
        _build_story(first_name, business, scores, competitors),
        onFirstPage=_header_footer,
        onLaterPages=_header_footer,
    )
    return buf.getvalue()
