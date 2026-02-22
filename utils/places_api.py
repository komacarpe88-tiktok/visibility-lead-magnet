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


def find_business(business_name: str, city: str) -> dict | None:
    """
    Search for a business by name and city using Text Search.
    Returns a dict with place_id, name, formatted_address, and geometry,
    or None if not found.
    """
    query = f"{business_name} {city}"
    params = {
        "query": query,
        "key": _api_key(),
    }
    try:
        resp = requests.get(f"{BASE_URL}/textsearch/json", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.error("Text Search request failed: %s", exc)
        raise

    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        logger.error("Places API error: %s — %s", data.get("status"), data.get("error_message"))
        raise ValueError(f"Places API error: {data.get('status')}")

    results = data.get("results", [])
    if not results:
        return None

    top = results[0]
    return {
        "place_id": top["place_id"],
        "name": top.get("name", business_name),
        "formatted_address": top.get("formatted_address", ""),
        "location": top.get("geometry", {}).get("location", {}),
        "types": top.get("types", []),
    }


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
    exclude_place_id: str,
    limit: int = 5,
) -> list[dict]:
    """
    Find nearby competitors of the same type.
    Returns a list of normalised profile dicts (up to `limit`).
    """
    if not location:
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
            f"Could not find '{business_name}' in '{city}' on Google Maps. "
            "Please check the business name and city and try again."
        )

    business_profile = get_place_details(search_result["place_id"])
    competitors = get_competitors(
        location=business_profile["location"],
        primary_type=business_profile["primary_type"],
        exclude_place_id=business_profile["place_id"],
        limit=5,
    )

    return {
        "business": business_profile,
        "competitors": competitors,
    }
