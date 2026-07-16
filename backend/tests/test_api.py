"""Endpoint tests (stateless API, no database).

Run with:  python manage.py test tests
Routing is mocked so no ORS key or network is required.
"""

from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

FAKE_COORDS = {
    "Dallas, TX": {"lat": 32.7767, "lng": -96.797, "label": "Dallas, TX"},
    "Oklahoma City, OK": {"lat": 35.4676, "lng": -97.5164, "label": "Oklahoma City, OK"},
    "Denver, CO": {"lat": 39.7392, "lng": -104.9903, "label": "Denver, CO"},
}


def fake_geocode(text):
    return FAKE_COORDS[text]


def fake_directions(coords):
    return {
        "distance_mi": 970.0,
        "duration_hr": 970 / 55,
        "geometry": {"type": "LineString",
                     "coordinates": [[lng, lat] for lat, lng in coords]},
        "leg_miles": [210.0, 760.0],
    }


VALID_INPUT = {
    "current_location": "Dallas, TX",
    "pickup_location": "Oklahoma City, OK",
    "dropoff_location": "Denver, CO",
    "current_cycle_used_hrs": 8,
}


class HealthEndpoint(SimpleTestCase):
    def test_health_ok(self):
        resp = self.client.get("/api/health/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})


class PlanEndpoint(SimpleTestCase):
    def _plan(self, payload=VALID_INPUT):
        with patch("api.planner.routing.geocode", side_effect=fake_geocode), \
             patch("api.planner.routing.directions", side_effect=fake_directions):
            return self.client.post("/api/plan/", payload, content_type="application/json")

    def test_plan_returns_payload(self):
        resp = self._plan()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["route"]["distance_mi"], 970.0)
        self.assertGreaterEqual(len(data["days"]), 1)
        for day in data["days"]:
            self.assertEqual(day["total_hours"], 24.0)

    def test_plan_is_stateless_no_id(self):
        # Nothing is persisted, so the response carries no trip id.
        self.assertNotIn("id", self._plan().json())

    def test_plan_rejects_out_of_range_cycle_hours(self):
        self.assertEqual(self._plan({**VALID_INPUT, "current_cycle_used_hrs": 999}).status_code, 400)

    def test_plan_rejects_missing_field(self):
        payload = {k: v for k, v in VALID_INPUT.items() if k != "dropoff_location"}
        self.assertEqual(self._plan(payload).status_code, 400)

    @override_settings(ORS_API_KEY="")
    def test_plan_without_key_returns_503(self):
        resp = self.client.post("/api/plan/", VALID_INPUT, content_type="application/json")
        self.assertEqual(resp.status_code, 503)

    def test_nan_cycle_hours_rejected(self):
        payload = {**VALID_INPUT, "current_cycle_used_hrs": "nan"}
        resp = self.client.post("/api/plan/", payload, content_type="application/json")
        self.assertEqual(resp.status_code, 400)


class GeocodeAutocompleteEndpoint(SimpleTestCase):
    def test_short_query_returns_empty(self):
        resp = self.client.get("/api/geocode/autocomplete/?text=Da")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"suggestions": []})

    def test_autocomplete_returns_suggestions(self):
        fake = [{"label": "Dallas, TX", "lat": 32.7, "lng": -96.8}]
        with patch("api.views.routing.autocomplete", return_value=fake):
            resp = self.client.get("/api/geocode/autocomplete/?text=Dallas")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["suggestions"], fake)

    @override_settings(ORS_API_KEY="")
    def test_autocomplete_without_key_returns_503(self):
        resp = self.client.get("/api/geocode/autocomplete/?text=Dallas")
        self.assertEqual(resp.status_code, 503)

    def test_autocomplete_upstream_error_returns_502(self):
        from routing import RoutingError
        with patch("api.views.routing.autocomplete", side_effect=RoutingError("boom")):
            resp = self.client.get("/api/geocode/autocomplete/?text=Dallas")
        self.assertEqual(resp.status_code, 502)
