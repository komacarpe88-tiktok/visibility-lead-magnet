"""
PDF-rapportgenerator med ReportLab.
Producerar en flersidigt, märkesanpassad synlighetsrapport på svenska.
"""

from __future__ import annotations

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Varumärkesfärger ───────────────────────────────────────────────────────────
NAVY      = colors.HexColor("#0D1B2A")
NAVY_LIGHT= colors.HexColor("#1A3050")
BLUE      = colors.HexColor("#1565C0")
CYAN      = colors.HexColor("#00B4D8")
GREEN     = colors.HexColor("#27AE60")
YELLOW    = colors.HexColor("#F39C12")
RED       = colors.HexColor("#E74C3C")
LIGHT_BG  = colors.HexColor("#F5F7FA")
GREY      = colors.HexColor("#8E9AAB")
GREY_LINE = colors.HexColor("#DEE2E6")
WHITE     = colors.white
BLACK     = colors.HexColor("#212529")

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
    return {
        "A": GREEN,
        "B": CYAN,
        "C": YELLOW,
        "D": colors.HexColor("#FF7043"),
        "F": RED,
    }.get(grade, GREY)


def _pct_bar(score: float, max_score: float, width: int = 15) -> str:
    """Returnerar en enkel textbaserad stapel, t.ex. '[=========------]  73%'"""
    pct = score / max_score if max_score else 0
    filled = int(pct * width)
    empty  = width - filled
    pct_str = f"{int(pct * 100)}%"
    return f"[{'=' * filled}{'-' * empty}]  {pct_str}"


def _status_sv(score: float, max_score: float) -> str:
    pct = score / max_score if max_score else 0
    if pct >= 0.7:
        return "Bra"
    if pct >= 0.4:
        return "OK"
    return "Svag"


def _make_styles() -> dict:
    styles = {
        "title": ParagraphStyle(
            "title", fontSize=26, leading=32, textColor=WHITE,
            fontName="Helvetica-Bold", alignment=TA_CENTER,
        ),
        "section_heading": ParagraphStyle(
            "section_heading", fontSize=13, leading=18, textColor=NAVY,
            fontName="Helvetica-Bold", spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body", fontSize=10, leading=15, textColor=BLACK, fontName="Helvetica",
        ),
        "body_centre": ParagraphStyle(
            "body_centre", fontSize=10, leading=15, textColor=BLACK,
            fontName="Helvetica", alignment=TA_CENTER,
        ),
        "score_big": ParagraphStyle(
            "score_big", fontSize=68, leading=76, fontName="Helvetica-Bold",
            alignment=TA_CENTER, textColor=WHITE,
        ),
        "score_label": ParagraphStyle(
            "score_label", fontSize=11, leading=16, fontName="Helvetica",
            textColor=GREY, alignment=TA_CENTER,
        ),
        "table_header": ParagraphStyle(
            "table_header", fontSize=9, leading=13, fontName="Helvetica-Bold",
            textColor=WHITE,
        ),
        "table_body": ParagraphStyle(
            "table_body", fontSize=9, leading=13, fontName="Helvetica", textColor=BLACK,
        ),
        "table_body_bold": ParagraphStyle(
            "table_body_bold", fontSize=9, leading=13, fontName="Helvetica-Bold", textColor=BLACK,
        ),
        "recommendation": ParagraphStyle(
            "recommendation", fontSize=10, leading=16, fontName="Helvetica",
            textColor=BLACK, leftIndent=14, spaceAfter=8,
        ),
        "footer": ParagraphStyle(
            "footer", fontSize=8, leading=12, textColor=GREY,
            fontName="Helvetica", alignment=TA_CENTER,
        ),
    }
    return styles


# ── Sidhuvud / sidfot ─────────────────────────────────────────────────────────

def _header_footer(canvas, doc):
    canvas.saveState()
    w, h = doc.pagesize

    # Övre fält
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 1.2 * cm, w, 1.2 * cm, fill=1, stroke=0)
    canvas.setFillColor(CYAN)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(MARGIN, h - 0.82 * cm, "LOKAL SYNLIGHETSRAPPORT")
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(w - MARGIN, h - 0.82 * cm,
                           f"Genererad {date.today().strftime('%d %B %Y')}")

    # Nedre fält
    canvas.setFillColor(LIGHT_BG)
    canvas.rect(0, 0, w, 1.1 * cm, fill=1, stroke=0)
    canvas.setFillColor(GREY)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(
        w / 2, 0.38 * cm,
        f"Konfidentiellt  |  Lokal Synlighetsrapport  |  Sida {doc.page}"
    )

    canvas.restoreState()


# ── Avsnitt 1: Framsida ───────────────────────────────────────────────────────

def _cover_section(styles, business: dict, scores: dict) -> list:
    elements = []
    score_colour = _grade_colour(scores["grade"])

    elements.append(Spacer(1, 1.2 * cm))

    # Stor poängcirkel (simulerad med färgad tabellcell)
    score_cell = Table(
        [[Paragraph(str(scores["total"]), styles["score_big"])]],
        colWidths=[5.5 * cm],
        rowHeights=[5.5 * cm],
    )
    score_cell.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), score_colour),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    wrapper = Table([[score_cell]], colWidths=[PAGE_W - 2 * MARGIN])
    wrapper.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    elements.append(wrapper)

    elements.append(Spacer(1, 0.25 * cm))
    elements.append(Paragraph("av 100 möjliga poäng", styles["score_label"]))
    elements.append(Spacer(1, 0.1 * cm))
    elements.append(Paragraph(f"<b>Betyg: {scores['grade']}</b>", styles["body_centre"]))

    elements.append(Spacer(1, 0.7 * cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=GREY_LINE))
    elements.append(Spacer(1, 0.5 * cm))

    info_data = [
        ["Företag",       business["name"]],
        ["Adress",        business.get("formatted_address", "—")],
        ["Betyg",         f"{business.get('rating', 'N/A')} stjärnor  ({business.get('review_count', 0):,} recensioner)"],
        ["Rapport skapad", date.today().strftime("%d %B %Y")],
    ]
    info_table = Table(info_data, colWidths=[4 * cm, PAGE_W - 2 * MARGIN - 4 * cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",      (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",     (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR",     (1, 0), (1, -1), BLACK),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW",     (0, 0), (-1, -2), 0.5, GREY_LINE),
    ]))
    elements.append(info_table)
    return elements


# ── Avsnitt 2: Poängfördelning ────────────────────────────────────────────────

def _score_breakdown_section(styles, scores: dict) -> list:
    elements = [PageBreak()]
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("Poängfördelning", styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=2, color=CYAN))
    elements.append(Spacer(1, 0.5 * cm))

    comp = scores.get("completeness_breakdown", {})
    completeness_detail = "  ".join([
        ("✓ Webb" if comp.get("has_website") else "✗ Webb"),
        ("✓ Tel" if comp.get("has_phone") else "✗ Tel"),
        ("✓ Tid" if comp.get("has_hours") else "✗ Tid"),
        ("✓ Kat" if comp.get("has_specific_categories") else "✗ Kat"),
    ])

    metrics = [
        ("Stjärnbetyg",         "rating_score",       35,
         "Baserat på ditt Google-stjärnbetyg (0–5)"),
        ("Antal recensioner",   "reviews_score",      30,
         "200+ = 30p  |  100+ = 26p  |  50+ = 21p  |  30+ = 17p  |  20+ = 12p  |  10+ = 7p"),
        ("Profilkomplettering", "completeness_score", 16,
         f"Webb(4p) + Tel(4p) + Oppettider(4p) + Kategorier(4p) | {completeness_detail}"),
        ("Antal foton",         "photos_score",       10,
         "10+ foton = maxpoang (API returnerar max 10 referenser)"),
        ("Svarsfrekvens",       "response_score",      6,
         "Andel av returnerade recensioner med agarsvar"),
        ("Foretagsbeskrivning", "description_score",   4,
         "Finns en Google-redaktionell sammanfattning?"),
    ]

    # Tabellhuvud
    header_style = TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY_LIGHT),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("TOPPADDING",    (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 9),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 9),
        ("TOPPADDING",    (0, 1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("GRID",          (0, 0), (-1, -1), 0.5, GREY_LINE),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (1, 0), (3, -1), "CENTER"),
    ])

    rows = [[
        Paragraph("Mått", styles["table_header"]),
        Paragraph("Poäng", styles["table_header"]),
        Paragraph("Max", styles["table_header"]),
        Paragraph("Stapel", styles["table_header"]),
        Paragraph("Status", styles["table_header"]),
        Paragraph("Kommentar", styles["table_header"]),
    ]]

    for label, key, max_pts, note in metrics:
        pts  = scores.get(key, 0)
        col  = _score_colour(pts, max_pts)
        bar  = _pct_bar(pts, max_pts, 12)
        stat = _status_sv(pts, max_pts)

        score_para = Paragraph(
            f"<b>{pts}</b>",
            ParagraphStyle("sp", parent=styles["table_body"],
                           textColor=col, fontName="Helvetica-Bold"),
        )
        status_para = Paragraph(
            f"<b>{stat}</b>",
            ParagraphStyle("st", parent=styles["table_body"],
                           textColor=col, fontName="Helvetica-Bold"),
        )

        rows.append([
            Paragraph(label, styles["table_body_bold"]),
            score_para,
            Paragraph(str(max_pts), styles["table_body"]),
            Paragraph(bar, ParagraphStyle("bar", parent=styles["table_body"],
                                          fontName="Courier", fontSize=7)),
            status_para,
            Paragraph(note, ParagraphStyle("note", parent=styles["table_body"],
                                           textColor=GREY, fontSize=8)),
        ])

    col_widths = [4.2 * cm, 1.4 * cm, 1.1 * cm, 3.8 * cm, 1.4 * cm, 5.1 * cm]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(header_style)
    elements.append(table)

    # Totalrad
    total_colour = _grade_colour(scores["grade"])
    elements.append(Spacer(1, 0.4 * cm))
    total_table = Table(
        [[
            Paragraph("<b>TOTAL SYNLIGHETSPOÄNG</b>",
                      ParagraphStyle("tl", parent=styles["body"], textColor=WHITE,
                                     fontName="Helvetica-Bold")),
            Paragraph(f"<b>{scores['total']} / 100</b>",
                      ParagraphStyle("tv", parent=styles["body"], textColor=WHITE,
                                     fontName="Helvetica-Bold", fontSize=13,
                                     alignment=TA_CENTER)),
            Paragraph(f"<b>Betyg {scores['grade']}</b>",
                      ParagraphStyle("tg", parent=styles["body"], textColor=WHITE,
                                     fontName="Helvetica-Bold", alignment=TA_CENTER)),
        ]],
        colWidths=[PAGE_W - 2 * MARGIN - 5 * cm, 3 * cm, 2 * cm],
    )
    total_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), total_colour),
        ("TEXTCOLOR",     (0, 0), (-1, -1), WHITE),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("ALIGN",         (1, 0), (2, 0), "CENTER"),
    ]))
    elements.append(total_table)
    return elements


# ── Avsnitt 3: Konkurrentjämförelse ──────────────────────────────────────────

def _competitor_section(styles, business: dict, competitors: list[dict], scores: dict) -> list:
    elements = [PageBreak()]
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("Lokal Konkurrentjämförelse", styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=2, color=CYAN))
    elements.append(Spacer(1, 0.35 * cm))
    elements.append(Paragraph(
        "Hur din Google Business-profil står sig mot de 5 närmaste konkurrenterna:",
        styles["body"],
    ))
    elements.append(Spacer(1, 0.35 * cm))

    from utils.scoring import calculate_score as calc

    ts = TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), NAVY_LIGHT),
        ("TEXTCOLOR",      (0, 0), (-1, 0), WHITE),
        ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, 0), 9),
        ("BACKGROUND",     (0, 1), (-1, 1), colors.HexColor("#DBEAFE")),
        ("FONTNAME",       (0, 1), (-1, 1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 2), (-1, -1), [WHITE, LIGHT_BG]),
        ("GRID",           (0, 0), (-1, -1), 0.5, GREY_LINE),
        ("FONTSIZE",       (0, 1), (-1, -1), 9),
        ("TOPPADDING",     (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 8),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 8),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",          (1, 0), (-1, -1), "CENTER"),
    ])

    rows = [[
        Paragraph("Företag",         styles["table_header"]),
        Paragraph("Betyg",           styles["table_header"]),
        Paragraph("Recensioner",     styles["table_header"]),
        Paragraph("Foton",           styles["table_header"]),
        Paragraph("Beskrivning",     styles["table_header"]),
        Paragraph("Synlighetspoäng", styles["table_header"]),
    ]]

    def _row(profile, score_val, is_you=False):
        name = f"{profile['name']} (DU)" if is_you else profile["name"]
        desc = "Ja" if profile.get("has_description") else "Nej"
        return [
            Paragraph(name, styles["table_body_bold"] if is_you else styles["table_body"]),
            Paragraph(f"{profile.get('rating', '—')} stjarnor", styles["table_body"]),
            Paragraph(f"{profile.get('review_count', 0):,}", styles["table_body"]),
            Paragraph(str(profile.get("photo_count", 0)), styles["table_body"]),
            Paragraph(desc, styles["table_body"]),
            Paragraph(f"<b>{score_val}</b>", styles["table_body_bold"]),
        ]

    rows.append(_row(business, scores["total"], is_you=True))
    for comp in competitors:
        comp_scores = calc(comp, [])
        rows.append(_row(comp, comp_scores["total"]))

    col_widths = [5 * cm, 2.2 * cm, 2.4 * cm, 1.6 * cm, 2.3 * cm, 3.5 * cm]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(ts)
    elements.append(table)
    return elements


# ── Avsnitt 4: Rekommendationer ───────────────────────────────────────────────

def _recommendations_section(styles, scores: dict) -> list:
    elements = [PageBreak()]
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("Rekommendationer för att förbättra din poäng",
                               styles["section_heading"]))
    elements.append(HRFlowable(width="100%", thickness=2, color=CYAN))
    elements.append(Spacer(1, 0.4 * cm))
    elements.append(Paragraph(
        "Baserat på din nuvarande Google Business-profil – här är de åtgärder som ger "
        "störst effekt på din lokala synlighet:",
        styles["body"],
    ))
    elements.append(Spacer(1, 0.35 * cm))

    for i, tip in enumerate(scores.get("recommendations", []), 1):
        elements.append(Paragraph(f"<b>{i}.</b>  {tip}", styles["recommendation"]))

    elements.append(Spacer(1, 0.8 * cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=GREY_LINE))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph(
        "<b>Vill du ha experthjälp med att implementera dessa förbättringar?</b>",
        styles["section_heading"],
    ))
    elements.append(Paragraph(
        "Vårt team specialiserar sig på lokal SEO och Google Business-profiloptimering. "
        "Boka ett gratis strategisamtal och låt oss hjälpa dig att dominera lokala sökresultat.",
        styles["body"],
    ))
    return elements


# ── Huvudfunktion ─────────────────────────────────────────────────────────────

def _build_story(first_name: str, business: dict, scores: dict, competitors: list[dict]) -> list:
    styles = _make_styles()
    story  = []
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
    Genererar en PDF-rapport helt i minnet och returnerar råa bytes.
    Inga filskrivningar – fungerar på ephemeral-hosting (Railway, Render, etc.).
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=1.8 * cm,
        bottomMargin=1.4 * cm,
        title=f"Lokal Synlighetsrapport – {business['name']}",
        author="LocalRankPro",
    )
    doc.build(
        _build_story(first_name, business, scores, competitors),
        onFirstPage=_header_footer,
        onLaterPages=_header_footer,
    )
    return buf.getvalue()
