"""Thin OpenRouteService client: geocoding, autocomplete, and directions.

The API key stays server-side (``settings.ORS_API_KEY``). Responses are cached
in Django's default cache keyed on the request so repeated lookups are cheap and
stay well under the free-tier quota.
"""

from __future__ import annotations

import hashlib
import json

import requests
from django.conf import settings
from django.core.cache import cache

METERS_PER_MILE = 1609.344
_TIMEOUT = 20

# Bias geocoding toward routable populated places / addresses. Excludes coarse
# admin layers (county/region/country) whose centroids can land off the road
# network and make ORS directions 404 ("no routable point").
_GEOCODE_LAYERS = "locality,localadmin,borough,neighbourhood,address,street,venue,postalcode"

# ORS snaps each waypoint to the nearest road; its default 350m radius is too
# small for some geocoded city centroids (they sit >350m from any road, even for
# cars). Bounded to ~5km so a city point reaches a nearby road without silently
# snapping a genuinely-off point to a faraway one.
_SNAP_RADIUS_M = 5000


class RoutingNotConfigured(RuntimeError):
    """Raised when no ORS API key is configured."""


class RoutingError(RuntimeError):
    """Raised when ORS returns an error or an unusable response."""


def _require_key() -> str:
    key = settings.ORS_API_KEY
    if not key:
        raise RoutingNotConfigured(
            "ORS_API_KEY is not set. Add it to backend/.env to enable routing."
        )
    return key


def _cache_key(*parts) -> str:
    raw = json.dumps(parts, sort_keys=True, default=str)
    return "ors:" + hashlib.sha256(raw.encode()).hexdigest()


def _request(method: str, path: str, *, what: str, **kwargs) -> dict:
    """Perform an ORS request and return parsed JSON, mapping every transport
    or decode failure to RoutingError (which views translate to 502)."""
    url = f"{settings.ORS_BASE_URL}{path}"
    try:
        resp = requests.request(method, url, timeout=_TIMEOUT, **kwargs)
    except requests.RequestException as exc:
        raise RoutingError(f"{what} unavailable: {exc}") from exc
    if not resp.ok:
        raise RoutingError(f"{what} failed ({resp.status_code})")
    try:
        return resp.json()
    except ValueError as exc:
        raise RoutingError(f"{what} returned a non-JSON response") from exc


def geocode(text: str) -> dict:
    """Resolve a free-text place to ``{lat, lng, label}`` (best match)."""
    key = _require_key()
    ck = _cache_key("geocode", text)
    if (hit := cache.get(ck)) is not None:
        return hit

    data = _request("GET", "/geocode/search", what="Geocoding",
                    params={"api_key": key, "text": text, "size": 1,
                            "layers": _GEOCODE_LAYERS})
    features = data.get("features") or []
    if not features:
        raise RoutingError(f"No location found for {text!r}")

    lng, lat = features[0]["geometry"]["coordinates"]
    result = {"lat": lat, "lng": lng, "label": features[0]["properties"].get("label", text)}
    cache.set(ck, result, settings.ROUTING_CACHE_SECONDS)
    return result


def autocomplete(text: str, size: int = 5) -> list[dict]:
    """Type-ahead suggestions: list of ``{label, lat, lng}``."""
    key = _require_key()
    ck = _cache_key("autocomplete", text, size)
    if (hit := cache.get(ck)) is not None:
        return hit

    data = _request("GET", "/geocode/autocomplete", what="Autocomplete",
                    params={"api_key": key, "text": text, "size": size,
                            "layers": _GEOCODE_LAYERS})

    suggestions = []
    for feat in data.get("features", []):
        lng, lat = feat["geometry"]["coordinates"]
        suggestions.append({
            "label": feat["properties"].get("label", ""),
            "lat": lat,
            "lng": lng,
        })
    cache.set(ck, suggestions, settings.ROUTING_CACHE_SECONDS)
    return suggestions


def directions(coordinates: list[tuple[float, float]]) -> dict:
    """Route through ``coordinates`` (list of ``(lat, lng)``).

    Returns total distance (miles), duration (hours), the GeoJSON LineString
    geometry, and per-leg distances in miles (one per waypoint gap).
    """
    key = _require_key()
    lnglat = [[lng, lat] for lat, lng in coordinates]
    ck = _cache_key("directions", lnglat)
    if (hit := cache.get(ck)) is not None:
        return hit

    data = _request(
        "POST", "/v2/directions/driving-hgv/geojson", what="Directions",
        json={"coordinates": lnglat, "radiuses": [_SNAP_RADIUS_M] * len(lnglat)},
        headers={"Authorization": key, "Content-Type": "application/json"},
    )
    features = data.get("features") or []
    if not features:
        raise RoutingError("Directions returned no route")
    props = features[0]["properties"]
    summary = props["summary"]
    leg_miles = [seg["distance"] / METERS_PER_MILE for seg in props.get("segments", [])]

    result = {
        "distance_mi": summary["distance"] / METERS_PER_MILE,
        "duration_hr": summary["duration"] / 3600.0,
        "geometry": features[0]["geometry"],  # GeoJSON LineString ([lng,lat] pairs)
        "leg_miles": leg_miles,
    }
    cache.set(ck, result, settings.ROUTING_CACHE_SECONDS)
    return result
