"""
Visibility Scoring Lead Magnet — Flask Application
"""

import io
import logging
import os
import threading
import uuid

import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

load_dotenv()

from utils.pdf_generator import generate_pdf_bytes
from utils.places_api import build_full_report_data
from utils.scoring import calculate_score

# ── App setup ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-me")

app.jinja_env.filters["zip"] = zip

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# Simple in-memory store: token → result dict
# PDFs are stored as bytes so no filesystem is needed (works on Railway).
_results_store: dict[str, dict] = {}


# ── GHL Webhook ────────────────────────────────────────────────────────────────

def _fire_ghl_webhook(payload: dict) -> None:
    """Fire-and-forget POST to the GHL webhook (runs in a daemon thread)."""
    webhook_url = os.getenv("GHL_WEBHOOK_URL", "")
    if not webhook_url or "REPLACE_ME" in webhook_url:
        logger.warning("GHL webhook URL not configured — skipping.")
        return
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("GHL webhook fired — status %s", resp.status_code)
    except requests.RequestException as exc:
        logger.error("GHL webhook failed: %s", exc)


def fire_webhook_async(payload: dict) -> None:
    t = threading.Thread(target=_fire_ghl_webhook, args=(payload,), daemon=True)
    t.start()


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    # ── Collect form data ──────────────────────────────────────────────────────
    first_name    = request.form.get("first_name", "").strip()
    email         = request.form.get("email", "").strip()
    phone         = request.form.get("phone", "").strip()
    business_name = request.form.get("business_name", "").strip()
    city          = request.form.get("city", "").strip()

    if not all([first_name, email, business_name, city]):
        flash("Please fill in all required fields.", "error")
        return redirect(url_for("index"))

    # ── Fetch data from Google Places ──────────────────────────────────────────
    try:
        report_data = build_full_report_data(business_name, city)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))
    except Exception as exc:
        logger.exception("Unexpected error fetching Places data: %s", exc)
        flash(
            "We encountered an error connecting to Google Places. Please try again shortly.",
            "error",
        )
        return redirect(url_for("index"))

    business    = report_data["business"]
    competitors = report_data["competitors"]

    # ── Score ──────────────────────────────────────────────────────────────────
    competitor_scores = [calculate_score(c, [])["total"] for c in competitors]

    # Top competitor by score (used in personalised copy)
    top_competitor = None
    top_competitor_name = None
    competitors_beating = 0
    review_ratio_text = "fler kunder från Google"

    if competitors and competitor_scores:
        top_idx = max(range(len(competitor_scores)), key=lambda i: competitor_scores[i])
        top_competitor = competitors[top_idx]
        top_competitor_name = top_competitor["name"]

    scores = calculate_score(business, competitors, top_competitor_name=top_competitor_name)

    if competitor_scores:
        competitors_beating = sum(1 for s in competitor_scores if s > scores["total"])

    if top_competitor:
        user_reviews = business.get("review_count", 1) or 1
        top_reviews  = top_competitor.get("review_count", 0)
        if top_reviews > user_reviews:
            ratio = top_reviews / user_reviews
            if ratio >= 3:
                review_ratio_text = f"{int(ratio)}x fler kunder från Google"
            elif ratio >= 2:
                review_ratio_text = "dubbelt så många kunder från Google"
            elif ratio >= 1.5:
                review_ratio_text = "50% fler kunder från Google"

    # ── Generate PDF (stored in memory as bytes) ───────────────────────────────
    pdf_bytes = None
    try:
        pdf_bytes = generate_pdf_bytes(first_name, business, scores, competitors)
        logger.info("PDF generated (%d bytes)", len(pdf_bytes))
    except Exception as exc:
        logger.exception("PDF generation failed: %s", exc)
        # Non-fatal — results page still renders without download button

    # ── GHL Webhook ────────────────────────────────────────────────────────────
    fire_webhook_async({
        "first_name":    first_name,
        "email":         email,
        "phone":         phone,
        "business_name": business_name,
        "city":          city,
        "score":         scores["total"],
        "grade":         scores["grade"],
    })

    # ── Store results ──────────────────────────────────────────────────────────
    token = uuid.uuid4().hex
    _results_store[token] = {
        "first_name":    first_name,
        "email":         email,
        "phone":         phone,
        "business_name": business_name,
        "city":          city,
        "business":      business,
        "competitors":        competitors,
        "competitor_scores":  competitor_scores,
        "scores":             scores,
        "top_competitor_name": top_competitor_name,
        "competitors_beating": competitors_beating,
        "review_ratio_text":  review_ratio_text,
        "pdf_bytes":     pdf_bytes,
    }

    return redirect(url_for("results", token=token))


@app.route("/results/<token>")
def results(token: str):
    data = _results_store.get(token)
    if not data:
        abort(404)
    # Pass pdf_path as truthy/falsy so template can show/hide download button
    return render_template(
        "results.html",
        token=token,
        pdf_path=bool(data.get("pdf_bytes")),
        **{k: v for k, v in data.items() if k != "pdf_bytes"},
    )


@app.route("/download/<token>")
def download(token: str):
    data = _results_store.get(token)
    if not data:
        abort(404)
    pdf_bytes = data.get("pdf_bytes")
    if not pdf_bytes:
        abort(404)
    business_name = data["business"]["name"].replace(" ", "_")
    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=f"Visibility_Report_{business_name}.pdf",
        mimetype="application/pdf",
    )


# ── Error handlers ─────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", message="Page not found."), 404


@app.errorhandler(500)
def server_error(_):
    return render_template("error.html", message="Something went wrong. Please try again."), 500


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", debug=False, port=port)
