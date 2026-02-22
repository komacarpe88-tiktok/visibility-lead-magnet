"""
Synlighetspoäng – beräkningsmotor.

Poäng av 100:
  - Stjärnbetyg                  25 p
  - Recensioner vs lokalt snitt  25 p
  - Antal foton                  20 p
  - Antal Google-kategorier      15 p
  - Företagsbeskrivning          10 p
  - Svarsfrekvens på recensioner  5 p
"""

from __future__ import annotations


def _rating_score(rating: float) -> float:
    """0–5 stjärnor → 0–25 p."""
    if not rating:
        return 0.0
    return round((min(rating, 5.0) / 5.0) * 25, 1)


def _reviews_score(review_count: int, competitor_avg: float) -> float:
    """Antal recensioner vs konkurrentsnitt → 0–25 p."""
    if competitor_avg <= 0:
        if review_count >= 100:
            return 25.0
        return round(min(review_count / 100, 1.0) * 25, 1)
    ratio = review_count / competitor_avg
    return round(min(ratio / 1.5, 1.0) * 25, 1)


def _photos_score(photo_count: int) -> float:
    """0–10+ foton → 0–20 p (API returnerar max 10)."""
    return round(min(photo_count / 10, 1.0) * 20, 1)


def _categories_score(type_count: int) -> float:
    """1–5+ Google-typer → 0–15 p."""
    return round(min(type_count / 5, 1.0) * 15, 1)


def _description_score(has_description: bool) -> float:
    """Företagsbeskrivning finns → 10 p."""
    return 10.0 if has_description else 0.0


def _response_rate_score(reviews_responded: int, reviews_returned: int) -> float:
    """Andel recensioner med ägarens svar → 0–5 p."""
    if reviews_returned == 0:
        return 0.0
    rate = reviews_responded / reviews_returned
    return round(rate * 5, 1)


def _get_recommendations(scores: dict, business: dict) -> list[str]:
    """Returnerar åtgärdsorienterade rekommendationer för låga delmått."""
    tips = []

    if scores["rating_score"] < 15:
        tips.append(
            "Ditt stjärnbetyg är under genomsnittet. Uppmana aktivt nöjda kunder att lämna "
            "5-stjärniga recensioner och hantera negativ feedback snabbt och professionellt."
        )
    if scores["reviews_score"] < 15:
        tips.append(
            "Du har färre recensioner än dina lokala konkurrenter. Kör en kampanj för att samla "
            "recensioner – ett enkelt SMS eller e-postmeddelande efter besöket fungerar utmärkt."
        )
    if scores["photos_score"] < 12:
        tips.append(
            "Din Google-profil behöver fler foton. Ladda upp högkvalitativa bilder av din butik, "
            "interiör, personal och produkter/tjänster för att öka trovärdigheten."
        )
    if scores["categories_score"] < 9:
        tips.append(
            "Din profil har få registrerade Google-typer. Se till att din Google Business-profil "
            "har rätt primär- och tilläggskategorier inställda för maximal synlighet."
        )
    if scores["description_score"] == 0:
        tips.append(
            "Du saknar en företagsbeskrivning. Lägg till en nyckelordsrik beskrivning i din "
            "Google Business-profil för att förbättra relevansen i sökresultaten."
        )
    if scores["response_score"] < 3:
        tips.append(
            "Svara på alla kundrecensioner – både positiva och negativa. Företag som svarar "
            "regelbundet rankar högre i lokala sökresultat och vinner kundernas förtroende."
        )

    if not tips:
        tips.append(
            "Din profil presterar bra! Fokusera på att upprätthålla en konsekvent "
            "recensionskampanj och håll din företagsinformation uppdaterad."
        )

    return tips


def calculate_score(business: dict, competitors: list[dict]) -> dict:
    """
    Beräknar synlighetspoäng för `business` relativt `competitors`.

    Returnerar ett dict med:
      - total, rating_score, reviews_score, photos_score,
        categories_score, description_score, response_score
      - competitor_avg_reviews
      - recommendations  (lista med strängar)
      - grade  ('A', 'B', 'C', 'D', 'F')
    """
    comp_review_counts = [c["review_count"] for c in competitors if c["review_count"]]
    competitor_avg = (
        sum(comp_review_counts) / len(comp_review_counts) if comp_review_counts else 0
    )

    rating_score      = _rating_score(business.get("rating", 0))
    reviews_score     = _reviews_score(business.get("review_count", 0), competitor_avg)
    photos_score      = _photos_score(business.get("photo_count", 0))
    categories_score  = _categories_score(len(business.get("types", [])))
    description_score = _description_score(business.get("has_description", False))
    response_score    = _response_rate_score(
        business.get("reviews_responded", 0),
        business.get("reviews_returned", 0),
    )

    total = int(
        rating_score + reviews_score + photos_score +
        categories_score + description_score + response_score
    )
    total = min(total, 100)

    scores = {
        "total": total,
        "rating_score": rating_score,
        "reviews_score": reviews_score,
        "photos_score": photos_score,
        "categories_score": categories_score,
        "description_score": description_score,
        "response_score": response_score,
        "competitor_avg_reviews": round(competitor_avg, 1),
    }

    scores["recommendations"] = _get_recommendations(scores, business)
    scores["grade"] = _grade(total)

    scores["max_scores"] = {
        "rating_score": 25,
        "reviews_score": 25,
        "photos_score": 20,
        "categories_score": 15,
        "description_score": 10,
        "response_score": 5,
    }

    return scores


def _grade(total: int) -> str:
    if total >= 85:
        return "A"
    if total >= 70:
        return "B"
    if total >= 55:
        return "C"
    if total >= 40:
        return "D"
    return "F"
