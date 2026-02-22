"""
Synlighetspoäng – beräkningsmotor.

Poäng av 100:
  - Stjärnbetyg                  25 p
  - Recensioner vs lokalt snitt  25 p
  - Antal foton (10+ = max)      20 p
  - Profilkomplettering          15 p
      webbplats (4p) + telefon (4p) + öppettider (4p) + kategorier (3p)
  - Företagsbeskrivning          10 p
  - Svarsfrekvens på recensioner  5 p
"""

from __future__ import annotations


def _rating_score(rating: float) -> float:
    if not rating:
        return 0.0
    return round((min(rating, 5.0) / 5.0) * 25, 1)


def _reviews_score(review_count: int, competitor_avg: float) -> float:
    if competitor_avg <= 0:
        if review_count >= 100:
            return 25.0
        return round(min(review_count / 100, 1.0) * 25, 1)
    ratio = review_count / competitor_avg
    return round(min(ratio / 1.5, 1.0) * 25, 1)


def _photos_score(photo_count: int) -> float:
    """10+ foton = maxpoäng (20p). API returnerar max 10."""
    return round(min(photo_count / 10, 1.0) * 20, 1)


def _completeness_score(
    has_website: bool,
    has_phone: bool,
    has_hours: bool,
    has_specific_categories: bool,
) -> tuple[float, dict]:
    """
    Profilkomplettering → 0–15 p
      Webbplats listad:          4 p
      Telefonnummer listat:      4 p
      Öppettider inställda:      4 p
      Specifika kategorier:      3 p
    """
    pts = (
        (4 if has_website else 0) +
        (4 if has_phone else 0) +
        (4 if has_hours else 0) +
        (3 if has_specific_categories else 0)
    )
    breakdown = {
        "has_website": has_website,
        "has_phone": has_phone,
        "has_hours": has_hours,
        "has_specific_categories": has_specific_categories,
    }
    return float(pts), breakdown


def _description_score(has_description: bool) -> float:
    return 10.0 if has_description else 0.0


def _response_rate_score(reviews_responded: int, reviews_returned: int) -> float:
    if reviews_returned == 0:
        return 0.0
    return round((reviews_responded / reviews_returned) * 5, 1)


def _get_recommendations(scores: dict, business: dict, top_competitor_name: str | None = None) -> list[str]:
    rival = top_competitor_name or "dina konkurrenter"
    tips  = []

    if scores["rating_score"] < 15:
        tips.append(
            f"Du förlorar kunder till {rival} varje dag på grund av ditt betyg — "
            f"det är det första potentiella kunder ser. Här är hur du fixar det på 48 timmar: "
            f"skicka ett enkelt SMS till dina senaste 20 kunder och be om en ärlig recension. "
            f"Svara på all negativ feedback professionellt inom 24 timmar."
        )
    if scores["reviews_score"] < 15:
        tips.append(
            f"{rival} dominerar sökresultaten delvis för att de har fler recensioner än dig. "
            f"Recensioner är den starkaste synlighetssignalen på Google. "
            f"Sätt upp ett automatiskt uppföljningsmeddelande efter varje avslutat jobb — "
            f"det tar 10 minuter att bygga och genererar recensioner på autopilot."
        )
    if scores["photos_score"] < 12:
        tips.append(
            f"Profiler med 10+ foton får upp till 35% fler klick än de utan. "
            f"Ladda upp minst 10 högkvalitativa bilder av din verksamhet — exteriör, interiör, "
            f"personal och arbete i fält. Det tar en timme och ger omedelbar effekt."
        )

    comp = scores.get("completeness_breakdown", {})
    if not comp.get("has_website"):
        tips.append(
            f"Du har ingen webbplats kopplad till din Google-profil. {rival} har det. "
            f"Google belönar kompletta profiler med bättre placeringar — lägg till din "
            f"webbadress direkt i Google Business-profilen."
        )
    if not comp.get("has_phone"):
        tips.append(
            f"Ditt telefonnummer saknas på Google. Kunder som hittar dig söker ofta "
            f"efter att ringa direkt — utan synligt nummer väljer de nästa företag i listan. "
            f"Lägg till numret i Google Business-profilen idag."
        )
    if not comp.get("has_hours"):
        tips.append(
            f"Du har inga öppettider inställda på Google. Det är en av de viktigaste "
            f"rankingfaktorerna för lokal sökning och en av de enklaste att fixa — "
            f"logga in i Google Business och lägg till dina tider nu."
        )
    if not comp.get("has_specific_categories"):
        tips.append(
            f"Din profil saknar specifika kategorier. Google använder kategorier för att "
            f"avgöra vilka sökningar du ska visas för — utan rätt kategorier missar du "
            f"kunder som söker exakt det du erbjuder."
        )
    if scores["description_score"] == 0:
        tips.append(
            f"Du saknar en företagsbeskrivning på Google. En välskriven, nyckelordsrik "
            f"beskrivning förbättrar din synlighet i sök och ger kunder en anledning att "
            f"välja dig framför {rival}."
        )
    if scores["response_score"] < 3:
        tips.append(
            f"Du svarar inte på dina recensioner. Google tolkar det som att du inte bryr "
            f"dig om dina kunder — och rankar dig därefter. Sätt av 10 minuter i veckan "
            f"för att svara på alla recensioner, positiva som negativa."
        )

    if not tips:
        tips.append(
            "Din profil presterar bra! Fokusera på att upprätthålla en konsekvent "
            "recensionskampanj och håll din företagsinformation uppdaterad."
        )

    return tips


def calculate_score(business: dict, competitors: list[dict], top_competitor_name: str | None = None) -> dict:
    comp_review_counts = [c["review_count"] for c in competitors if c["review_count"]]
    competitor_avg = (
        sum(comp_review_counts) / len(comp_review_counts) if comp_review_counts else 0
    )

    rating_score      = _rating_score(business.get("rating", 0))
    reviews_score     = _reviews_score(business.get("review_count", 0), competitor_avg)
    photos_score      = _photos_score(business.get("photo_count", 0))
    completeness_score, completeness_breakdown = _completeness_score(
        has_website=business.get("has_website", False),
        has_phone=business.get("has_phone", False),
        has_hours=business.get("has_hours", False),
        has_specific_categories=business.get("has_specific_categories", False),
    )
    description_score = _description_score(business.get("has_description", False))
    response_score    = _response_rate_score(
        business.get("reviews_responded", 0),
        business.get("reviews_returned", 0),
    )

    total = int(
        rating_score + reviews_score + photos_score +
        completeness_score + description_score + response_score
    )
    total = min(total, 100)

    scores = {
        "total": total,
        "rating_score": rating_score,
        "reviews_score": reviews_score,
        "photos_score": photos_score,
        "completeness_score": completeness_score,
        "completeness_breakdown": completeness_breakdown,
        "description_score": description_score,
        "response_score": response_score,
        "competitor_avg_reviews": round(competitor_avg, 1),
    }

    scores["recommendations"] = _get_recommendations(scores, business, top_competitor_name)
    scores["grade"] = _grade(total)

    scores["max_scores"] = {
        "rating_score": 25,
        "reviews_score": 25,
        "photos_score": 20,
        "completeness_score": 15,
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
