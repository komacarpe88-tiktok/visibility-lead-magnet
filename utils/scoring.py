"""
Visibility score calculation.

Score out of 100:
  - Rating                  25 pts
  - Reviews vs local avg    25 pts
  - Photo count             20 pts
  - Category count          15 pts
  - Description present     10 pts
  - Review response rate     5 pts
"""

from __future__ import annotations


def _rating_score(rating: float) -> float:
    """0–5 star rating → 0–25 pts."""
    if not rating:
        return 0.0
    return round((min(rating, 5.0) / 5.0) * 25, 1)


def _reviews_score(review_count: int, competitor_avg: float) -> float:
    """
    Review count vs competitor average → 0–25 pts.
    At the average you get 20 pts; above-average scales to 25.
    """
    if competitor_avg <= 0:
        # No competitor data — score on absolute count alone
        if review_count >= 100:
            return 25.0
        return round(min(review_count / 100, 1.0) * 25, 1)

    ratio = review_count / competitor_avg
    # Cap at 1.5× average for full marks
    return round(min(ratio / 1.5, 1.0) * 25, 1)


def _photos_score(photo_count: int) -> float:
    """0–10+ photos → 0–20 pts (10 is the API return cap)."""
    return round(min(photo_count / 10, 1.0) * 20, 1)


def _categories_score(type_count: int) -> float:
    """1–5+ types → 0–15 pts."""
    return round(min(type_count / 5, 1.0) * 15, 1)


def _description_score(has_description: bool) -> float:
    """Google editorial summary present → 10 pts."""
    return 10.0 if has_description else 0.0


def _response_rate_score(reviews_responded: int, reviews_returned: int) -> float:
    """
    Of the reviews returned by the API (up to 5), how many have an owner reply?
    → 0–5 pts.
    """
    if reviews_returned == 0:
        return 0.0
    rate = reviews_responded / reviews_returned
    return round(rate * 5, 1)


def _get_recommendations(scores: dict, business: dict) -> list[str]:
    """Return actionable recommendations for low-scoring metrics."""
    tips = []

    if scores["rating_score"] < 15:
        tips.append(
            "Your rating is below average. Actively ask satisfied customers to leave "
            "5-star reviews and address any negative feedback promptly."
        )
    if scores["reviews_score"] < 15:
        tips.append(
            "You have fewer reviews than local competitors. Consider running a review "
            "generation campaign — a simple follow-up text or email works well."
        )
    if scores["photos_score"] < 12:
        tips.append(
            "Your Google Business Profile needs more photos. Upload high-quality "
            "images of your storefront, interior, team, and products/services."
        )
    if scores["categories_score"] < 9:
        tips.append(
            "Add more relevant business categories in your Google Business Profile "
            "to improve visibility across more search terms."
        )
    if scores["description_score"] == 0:
        tips.append(
            "You're missing a business description. Add a keyword-rich description "
            "in your Google Business Profile to improve search relevance."
        )
    if scores["response_score"] < 3:
        tips.append(
            "Respond to all customer reviews — both positive and negative. "
            "Businesses that respond regularly rank higher in local search results."
        )

    if not tips:
        tips.append(
            "Your profile is performing well! Focus on maintaining consistent "
            "review generation and keep your business information up to date."
        )

    return tips


def calculate_score(business: dict, competitors: list[dict]) -> dict:
    """
    Calculate a visibility score for `business` relative to `competitors`.

    Returns a dict containing:
      - total          (int 0–100)
      - rating_score, reviews_score, photos_score,
        categories_score, description_score, response_score
      - competitor_avg_reviews
      - recommendations  (list of strings)
      - grade  ('A', 'B', 'C', 'D', 'F')
    """
    # Competitor average review count
    comp_review_counts = [c["review_count"] for c in competitors if c["review_count"]]
    competitor_avg = (
        sum(comp_review_counts) / len(comp_review_counts) if comp_review_counts else 0
    )

    rating_score       = _rating_score(business.get("rating", 0))
    reviews_score      = _reviews_score(business.get("review_count", 0), competitor_avg)
    photos_score       = _photos_score(business.get("photo_count", 0))
    categories_score   = _categories_score(len(business.get("types", [])))
    description_score  = _description_score(business.get("has_description", False))
    response_score     = _response_rate_score(
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

    # Max possible per metric (for display)
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
