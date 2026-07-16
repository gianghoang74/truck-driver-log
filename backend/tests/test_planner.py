"""Planner tests using a fake routing backend (no network / API key needed)."""

import unittest
from datetime import datetime

import routing
from api import planner
from api.planner import _point_at_mile


class FakeRouting:
    """Stand-in for the ORS client with deterministic coordinates/distances."""

    COORDS = {
        "Dallas, TX": {"lat": 32.7767, "lng": -96.7970, "label": "Dallas, TX"},
        "Oklahoma City, OK": {"lat": 35.4676, "lng": -97.5164, "label": "Oklahoma City, OK"},
        "Denver, CO": {"lat": 39.7392, "lng": -104.9903, "label": "Denver, CO"},
    }

    @staticmethod
    def geocode(text):
        return FakeRouting.COORDS[text]

    @staticmethod
    def directions(coordinates):
        # current->pickup 210mi, pickup->dropoff 680mi (roughly OKC->Denver).
        return {
            "distance_mi": 890.0,
            "duration_hr": 890.0 / 55.0,
            "geometry": {"type": "LineString",
                         "coordinates": [[lng, lat] for lat, lng in coordinates]},
            "leg_miles": [210.0, 680.0],
        }


class PlanTripAssembly(unittest.TestCase):
    def setUp(self):
        self._orig = (routing.geocode, routing.directions)
        routing.geocode = FakeRouting.geocode
        routing.directions = FakeRouting.directions
        self.result = planner.plan_trip(
            "Dallas, TX", "Oklahoma City, OK", "Denver, CO",
            cycle_used_hrs=10.0,
            start=datetime(2026, 7, 16, 8, 0),
        )

    def tearDown(self):
        routing.geocode, routing.directions = self._orig

    def test_route_summary(self):
        self.assertEqual(self.result["route"]["distance_mi"], 890.0)
        self.assertAlmostEqual(self.result["route"]["drive_hrs"], 890.0 / 55.0, places=2)

    def test_has_pickup_and_dropoff_with_coords(self):
        by_type = {s["type"]: s for s in self.result["stops"]}
        self.assertIn("pickup", by_type)
        self.assertIn("dropoff", by_type)
        self.assertEqual(by_type["dropoff"]["coordinates"], [-104.9903, 39.7392])

    def test_days_present_and_sum_to_24(self):
        self.assertGreater(len(self.result["days"]), 0)
        for day in self.result["days"]:
            self.assertEqual(day["total_hours"], 24.0)

    def test_recap_carries_cycle_used(self):
        first = self.result["days"][0]["recap"]
        # 10 starting hrs + first day's on-duty time.
        self.assertGreaterEqual(first["used_last_8_days"], 10.0)


class PointAtMile(unittest.TestCase):
    def test_interpolates_by_distance_not_vertex_index(self):
        # Vertices clustered near the start; halfway by DISTANCE is ~0.5 lat,
        # whereas halfway by vertex index would wrongly give the 0.1 vertex.
        geom = {"type": "LineString", "coordinates": [[0, 0], [0, 0.1], [0, 1.0]]}
        pt = _point_at_mile(geom, 50, 100)
        self.assertAlmostEqual(pt[1], 0.5, delta=0.05)

    def test_endpoints(self):
        geom = {"type": "LineString", "coordinates": [[0, 0], [0, 1.0]]}
        self.assertEqual(_point_at_mile(geom, 0, 100)[1], 0.0)
        self.assertAlmostEqual(_point_at_mile(geom, 100, 100)[1], 1.0, places=6)

    def test_degenerate_geometry(self):
        self.assertIsNone(_point_at_mile({"coordinates": []}, 10, 100))


if __name__ == "__main__":
    unittest.main()
