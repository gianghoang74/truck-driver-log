"""Trip planning service: geocode + route + run the HOS engine.

Ties the routing client to the pure-Python engine and shapes the API payload
(route summary, stops with map coordinates, per-day logs). Kept separate from
the views so it can be unit-tested with a fake routing backend.
"""

from __future__ import annotations

import math
from datetime import date, datetime, time

from hos import constants as C
from hos.engine import Leg, build_days, simulate

# Injection seam: tests replace these with fakes so no network/key is needed.
import routing

_EARTH_RADIUS_MI = 3958.7613


def _haversine_mi(a: list, b: list) -> float:
    """Great-circle distance in miles between two ``[lng, lat]`` points."""
    lng1, lat1, lng2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2)
    return 2 * _EARTH_RADIUS_MI * math.asin(math.sqrt(h))


def _point_at_mile(geometry: dict, mile: float, total_miles: float) -> list | None:
    """Interpolate a ``[lng, lat]`` point at a fraction of the route's actual
    geometric length (by cumulative distance, not vertex index — ORS vertices
    are not evenly spaced)."""
    coords = (geometry or {}).get("coordinates") or []
    if len(coords) < 2 or total_miles <= 0:
        return coords[0] if coords else None

    seg_lens = [_haversine_mi(coords[i], coords[i + 1]) for i in range(len(coords) - 1)]
    poly_len = sum(seg_lens)
    if poly_len <= 0:
        return coords[0]

    frac = min(max(mile / total_miles, 0.0), 1.0)
    target = frac * poly_len
    acc = 0.0
    for i, seg_len in enumerate(seg_lens):
        if acc + seg_len >= target or i == len(seg_lens) - 1:
            t = 0.0 if seg_len == 0 else (target - acc) / seg_len
            (lng0, lat0), (lng1, lat1) = coords[i][:2], coords[i + 1][:2]
            return [lng0 + (lng1 - lng0) * t, lat0 + (lat1 - lat0) * t]
        acc += seg_len
    return coords[-1]


def plan_trip(current: str, pickup: str, dropoff: str, cycle_used_hrs: float,
              start: datetime | None = None) -> dict:
    """Produce the full plan payload for the four trip inputs."""
    c = routing.geocode(current)
    p = routing.geocode(pickup)
    d = routing.geocode(dropoff)

    route = routing.directions([(c["lat"], c["lng"]),
                                (p["lat"], p["lng"]),
                                (d["lat"], d["lng"])])
    leg_miles = route["leg_miles"]
    if len(leg_miles) != 2:  # defensive: expect exactly current->pickup, pickup->dropoff
        half = route["distance_mi"] / 2
        leg_miles = [half, half]

    legs = [
        Leg(leg_miles[0], to_label=p["label"], from_label=c["label"]),
        Leg(leg_miles[1], to_label=d["label"], from_label=p["label"]),
    ]

    if start is None:
        start = datetime.combine(date.today(), time(hour=8))

    plan = simulate(legs, cycle_used_hrs=cycle_used_hrs, start=start)
    days = build_days(plan.segments, cycle_used_start=cycle_used_hrs)

    total = plan.total_miles
    endpoint_coords = {"pickup": [p["lng"], p["lat"]], "dropoff": [d["lng"], d["lat"]]}

    stops = []
    for s in plan.stops:
        coords = endpoint_coords.get(s.type) or _point_at_mile(
            route["geometry"], s.mile, total)
        stops.append({
            "type": s.type,
            "label": s.label or s.location,
            "arrive": s.start.isoformat(),
            "duration_hrs": round(s.duration_hrs, 2),
            "mile": round(s.mile, 1),
            "coordinates": coords,
            "satisfies_break": s.satisfies_break,
        })

    return {
        "inputs": {
            "current_location": c["label"],
            "pickup_location": p["label"],
            "dropoff_location": d["label"],
            "current_cycle_used_hrs": cycle_used_hrs,
        },
        "route": {
            "distance_mi": round(total, 1),
            "drive_hrs": round(total / C.AVG_SPEED_MPH, 2),
            "geometry": route["geometry"],
            "waypoints": {
                "current": [c["lng"], c["lat"]],
                "pickup": [p["lng"], p["lat"]],
                "dropoff": [d["lng"], d["lat"]],
            },
        },
        "stops": stops,
        "days": days,
    }
