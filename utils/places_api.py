"""
Google Places API utilities for the visibility scoring tool.
Uses the legacy Places API (maps.googleapis.com).
"""

import os
import requests
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://maps.googleapis.com/maps/api/place"

DETAIL_FIELDS = (
    "name,rating,user_ratings_total,photos,types,"
    "editorial_summary,reviews,formatted_address,"
    "geometry,business_status,"
    "website,formatted_phone_number,opening_hours"
)

# Types to skip when selecting the primary competitor search type
GENERIC_TYPES = {
    "establishment", "point_of_interest", "food", "store",
    "health", "finance", "local_government_office"
}


def _api_key():
    return os.getenv("GOOGLE_PLACES_API_KEY", "")


def _same_industry(business_types: list, competitor_types: list) -> bool:
    """Return True if two businesses share at least one specific (non-generic) type."""
    biz_specific  = {t for t in business_types  if t not in GENERIC_TYPES}
    comp_specific = {t for t in competitor_types if t not in GENERIC_TYPES}
    return bool(biz_specific & comp_specific)


def _textsearch(query: str) -> dict | None:
    """Run a single Text Search query and return the first result, or None."""
    params = {"query": query, "key": _api_key()}
    try:
        resp = requests.get(f"{BASE_URL}/textsearch/json", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.error("Text Search request failed: %s", exc)
        raise

    status = data.get("status")
    if status not in ("OK", "ZERO_RESULTS"):
        raise ValueError(f"Places API error: {status} — {data.get('error_message')}")

    results = data.get("results", [])
    if not results:
        return None

    top = results[0]
    return {
        "place_id": top["place_id"],
        "name": top.get("name", ""),
        "formatted_address": top.get("formatted_address", ""),
        "location": top.get("geometry", {}).get("location", {}),
        "types": top.get("types", []),
    }


def _simplify_name(name: str) -> str:
    """Strip common Swedish/English legal suffixes to broaden search."""
    import re
    return re.sub(
        r"\b(AB|HB|KB|Aktiebolag|Ltd|GmbH|Inc|LLC|Ek\.?för\.?|ekonomisk förening)\b",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip(" ,.-")


def _names_match(search_name: str, result_name: str) -> bool:
    """
    Check that the result is plausibly the right business.
    At least one significant word (4+ chars) from the search must appear
    in the result name (case-insensitive).
    """
    search_words = {w.lower() for w in search_name.split() if len(w) >= 4}
    result_lower = result_name.lower()
    return any(w in result_lower for w in search_words)


def find_business(business_name: str, city: str) -> dict | None:
    """
    Search for a business using progressively broader queries,
    but only accept a result whose name matches the original search.
    """
    simplified = _simplify_name(business_name)

    queries = [
        f"{business_name} {city}",   # exact name + city  (most specific)
        f"{business_name}",           # exact name, no city
        f"{simplified} {city}",       # stripped suffix + city
        f"{simplified}",              # stripped suffix, no city
    ]

    seen, unique = set(), []
    for q in queries:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            unique.append(q)

    for query in unique:
        logger.info("Trying Places search: %s", query)
        result = _textsearch(query)
        if result and _names_match(business_name, result["name"]):
            logger.info("Matched: %s", result["name"])
            return result
        if result:
            logger.info("Rejected (name mismatch): search=%r result=%r", business_name, result["name"])

    return None


def get_place_details(place_id: str) -> dict:
    """
    Fetch full details for a place, including rating, reviews, photos, etc.
    Returns a normalised business profile dict.
    """
    params = {
        "place_id": place_id,
        "fields": DETAIL_FIELDS,
        "key": _api_key(),
    }
    try:
        resp = requests.get(f"{BASE_URL}/details/json", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.error("Place Details request failed: %s", exc)
        raise

    if data.get("status") != "OK":
        logger.error("Place Details error: %s", data.get("status"))
        raise ValueError(f"Place Details error: {data.get('status')}")

    result = data.get("result", {})
    return _normalise_details(place_id, result)


def _normalise_details(place_id: str, result: dict) -> dict:
    """Convert a raw Places API result into a clean profile dict."""
    photos = result.get("photos", [])
    reviews = result.get("reviews", [])

    # Review response rate: count reviews that have an owner_response
    responded = sum(1 for r in reviews if r.get("owner_response"))
    total_reviews_returned = len(reviews)

    # Primary type: first non-generic type
    types = result.get("types", [])
    primary_type = next(
        (t for t in types if t not in GENERIC_TYPES),
        types[0] if types else "establishment"
    )

    description = result.get("editorial_summary", {}).get("overview", "")

    # Profile completeness signals
    has_website  = bool(result.get("website", ""))
    has_phone    = bool(result.get("formatted_phone_number", ""))
    has_hours    = bool(result.get("opening_hours", {}).get("weekday_text"))
    # Specific (non-generic) category = at least one type outside the generic set
    has_specific_categories = any(t not in GENERIC_TYPES for t in types)

    return {
        "place_id": place_id,
        "name": result.get("name", ""),
        "formatted_address": result.get("formatted_address", ""),
        "location": result.get("geometry", {}).get("location", {}),
        "rating": result.get("rating", 0.0),
        "review_count": result.get("user_ratings_total", 0),
        "photo_count": len(photos),           # capped at 10 by API
        "photo_count_capped": len(photos) >= 10,  # True = business has 10+ photos
        "types": types,
        "primary_type": primary_type,
        "has_description": bool(description),
        "description": description,
        "reviews_returned": total_reviews_returned,
        "reviews_responded": responded,
        # Profile completeness
        "has_website": has_website,
        "has_phone": has_phone,
        "has_hours": has_hours,
        "has_specific_categories": has_specific_categories,
    }


def get_competitors(
    location: dict,
    primary_type: str,
    business_types: list,
    exclude_place_id: str,
    limit: int = 5,
) -> list[dict]:
    """
    Find nearby competitors of the same type.
    Returns a list of normalised profile dicts (up to `limit`).

    If the business only has generic types (e.g. point_of_interest), nearby
    search would return random prominent places (hotels, restaurants, etc.).
    In that case we bail out early and return an empty list.
    """
    if not location:
        return []

    # Guard: if the resolved type is still generic the search would return
    # completely unrelated places — skip competitor fetching entirely.
    if primary_type in GENERIC_TYPES:
        logger.warning(
            "primary_type '%s' is generic — skipping competitor search", primary_type
        )
        return []

    params = {
        "location": f"{location['lat']},{location['lng']}",
        "radius": 8000,           # 8 km radius
        "type": primary_type,
        "key": _api_key(),
    }
    try:
        resp = requests.get(f"{BASE_URL}/nearbysearch/json", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.error("Nearby Search request failed: %s", exc)
        return []

    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        logger.warning("Nearby Search status: %s", data.get("status"))
        return []

    competitors = []
    for place in data.get("results", []):
        pid = place.get("place_id")
        if not pid or pid == exclude_place_id:
            continue
        try:
            profile = get_place_details(pid)
            # Reject businesses from a completely different industry
            if not _same_industry(business_types, profile["types"]):
                logger.info(
                    "Skipping '%s' — different industry (types: %s)",
                    profile["name"], profile["types"],
                )
                continue
            competitors.append(profile)
        except Exception as exc:
            logger.warning("Skipping competitor %s: %s", pid, exc)
            continue

        if len(competitors) >= limit:
            break

    return competitors


def build_full_report_data(business_name: str, city: str) -> dict:
    """
    Top-level helper: find business, get details, get competitors.
    Returns { business: profile, competitors: [profile, ...] }
    or raises ValueError if the business cannot be found.
    """
    search_result = find_business(business_name, city)
    if search_result is None:
        raise ValueError(
            f"Vi kunde inte hitta '{business_name}' på Google Maps. "
            "Kontrollera att företagsnamnet stämmer exakt och att staden är korrekt, och försök igen."
        )

    business_profile = get_place_details(search_result["place_id"])

    # Fetch more candidates than needed so we can filter out large chains
    raw_competitors = get_competitors(
        location=business_profile["location"],
        primary_type=business_profile["primary_type"],
        business_types=business_profile["types"],
        exclude_place_id=business_profile["place_id"],
        limit=10,
    )

    competitors = _filter_local_competitors(
        raw_competitors,
        own_review_count=business_profile["review_count"],
        want=5,
    )

    return {
        "business": business_profile,
        "competitors": competitors,
    }


def _filter_local_competitors(
    candidates: list[dict],
    own_review_count: int,
    want: int = 5,
) -> list[dict]:
    """
    Remove disproportionately large chains before benchmarking.

    Strategy:
      - Cap = max(own_review_count × 25, 300)
        e.g. a business with 12 reviews → cap at 300
             a business with 100 reviews → cap at 2 500
      - Keep candidates under the cap, sorted by review count descending
        so we use the most-reviewed local businesses first.
      - If filtering leaves fewer than 2 results, fall back to the
        original list (better than no comparison at all).
    """
    own = max(own_review_count, 1)
    cap = max(own * 25, 300)

    local = [c for c in candidates if c["review_count"] <= cap]
    local.sort(key=lambda c: c["review_count"], reverse=True)

    if len(local) >= 2:
        logger.info(
            "Competitor filter: kept %d/%d (cap=%d reviews)",
            len(local), len(candidates), cap,
        )
        return local[:want]

    # Fallback: all candidates, take the ones closest in size to the target
    logger.warning(
        "Competitor filter: fewer than 2 local results after filtering — using closest by size"
    )
    candidates_sorted = sorted(
        candidates,
        key=lambda c: abs(c["review_count"] - own),
    )
    return candidates_sorted[:want]
