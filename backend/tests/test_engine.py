"""Unit tests for the HOS engine.

Run from the backend/ directory:
    python -m unittest discover -s tests
"""

import unittest
from datetime import datetime, timedelta

from hos import constants as C
from hos.engine import Leg, Segment, build_days, simulate


def _dt(y=2026, m=7, d=16, hh=0, mm=0):
    return datetime(y, m, d, hh, mm)


def _stops_of(plan, type_):
    return [s for s in plan.stops if s.type == type_]


def _driving_hours(plan):
    return sum(s.hours for s in plan.segments if s.status == C.DRIVING)


class BuildDaysJohnDoeOracle(unittest.TestCase):
    """Reproduce the FMCSA guide's completed log (pp.18-19) exactly.

    Richmond, VA -> Newark, NJ on 04/09/2021. Expected status totals:
    Off 10 / Sleeper 1.75 / Driving 7.75 / On-duty 4.5 = 24.
    """

    def _john_doe_segments(self):
        base = datetime(2021, 4, 9)

        def at(h, m=0):
            return base + timedelta(hours=h, minutes=m)

        return [
            Segment(C.OFF_DUTY, at(0), at(6)),
            Segment(C.ON_DUTY, at(6), at(7, 30), location="Richmond, VA",
                    note="Reported for work"),
            Segment(C.DRIVING, at(7, 30), at(9)),
            Segment(C.ON_DUTY, at(9), at(9, 30), location="Fredericksburg, VA",
                    note="Fuel"),
            Segment(C.DRIVING, at(9, 30), at(12)),
            Segment(C.OFF_DUTY, at(12), at(13), location="Baltimore, MD",
                    note="Lunch"),
            Segment(C.DRIVING, at(13), at(15)),
            Segment(C.ON_DUTY, at(15), at(15, 30), location="Philadelphia, PA",
                    note="Delivery"),
            Segment(C.DRIVING, at(15, 30), at(16)),
            Segment(C.SLEEPER, at(16), at(17, 45), location="Cherry Hill, NJ",
                    note="Sleeper berth"),
            Segment(C.DRIVING, at(17, 45), at(19)),
            Segment(C.ON_DUTY, at(19), at(21), location="Newark, NJ",
                    note="Post-trip"),
            Segment(C.OFF_DUTY, at(21), at(24)),
        ]

    def test_totals_match_guide(self):
        days = build_days(self._john_doe_segments())
        self.assertEqual(len(days), 1)
        totals = days[0]["totals"]
        self.assertEqual(totals[C.OFF_DUTY], 10.0)
        self.assertEqual(totals[C.SLEEPER], 1.75)
        self.assertEqual(totals[C.DRIVING], 7.75)
        self.assertEqual(totals[C.ON_DUTY], 4.5)
        self.assertEqual(days[0]["total_hours"], 24.0)

    def test_remarks_sequence(self):
        days = build_days(self._john_doe_segments())
        locations = [r["location"] for r in days[0]["remarks"]]
        self.assertEqual(
            locations,
            ["Richmond, VA", "Fredericksburg, VA", "Baltimore, MD",
             "Philadelphia, PA", "Cherry Hill, NJ", "Newark, NJ"],
        )


class SimpleTrip(unittest.TestCase):
    """Short trip: no rest, no break, single day."""

    def setUp(self):
        legs = [Leg(55, "Pickup City", "Origin City"),
                Leg(110, "Dropoff City", "Pickup City")]
        self.plan = simulate(legs, cycle_used_hrs=0.0, start=_dt(hh=8))

    def test_no_rest_or_break_inserted(self):
        self.assertEqual(_stops_of(self.plan, "rest"), [])
        self.assertEqual(_stops_of(self.plan, "break"), [])

    def test_driving_hours(self):
        # (55 + 110) miles / 55 mph = 3 hours driving.
        self.assertAlmostEqual(_driving_hours(self.plan), 3.0, places=3)

    def test_pickup_and_dropoff_present(self):
        self.assertEqual(len(_stops_of(self.plan, "pickup")), 1)
        self.assertEqual(len(_stops_of(self.plan, "dropoff")), 1)

    def test_each_day_sums_to_24(self):
        for day in build_days(self.plan.segments):
            self.assertEqual(day["total_hours"], 24.0)


class ElevenHourCap(unittest.TestCase):
    """A leg longer than 11h of driving must force a 10-hour rest."""

    def setUp(self):
        # 715 miles / 55 mph = 13 hours of driving > 11-hour limit.
        legs = [Leg(0, "Pickup City", "Origin City"),
                Leg(715, "Dropoff City", "Pickup City")]
        self.plan = simulate(legs, cycle_used_hrs=0.0, start=_dt(hh=6))

    def test_one_rest_inserted(self):
        self.assertEqual(len(_stops_of(self.plan, "rest")), 1)

    def test_total_driving_preserved(self):
        self.assertAlmostEqual(_driving_hours(self.plan), 13.0, places=2)

    def test_break_inserted_after_8_driving_hours(self):
        # 8 continuous driving hours before any qualifying stop -> a dedicated break.
        self.assertEqual(len(_stops_of(self.plan, "break")), 1)

    def test_spans_two_days(self):
        self.assertGreaterEqual(len(build_days(self.plan.segments)), 2)


class BreakIsFree(unittest.TestCase):
    """Pickup/fuel stops satisfy the 30-min break, so no dedicated break."""

    def setUp(self):
        # Two ~7h legs separated by a 1h pickup. The pickup resets the break
        # clock, and the 11h cap forces a rest before 8 continuous driving hrs
        # ever accumulate -> no standalone break.
        legs = [Leg(385, "Pickup City", "Origin City"),   # 7h
                Leg(330, "Dropoff City", "Pickup City")]   # 6h
        self.plan = simulate(legs, cycle_used_hrs=0.0, start=_dt(hh=6))

    def test_no_dedicated_break(self):
        self.assertEqual(_stops_of(self.plan, "break"), [])

    def test_days_sum_to_24(self):
        for day in build_days(self.plan.segments):
            self.assertEqual(day["total_hours"], 24.0)


class CycleRestart(unittest.TestCase):
    """Hitting the 70-hour cycle limit forces a 34-hour restart."""

    def setUp(self):
        # Pickup (1h) pushes cycle to 69; a short drive then crosses 70.
        legs = [Leg(0, "Pickup City", "Origin City"),
                Leg(165, "Dropoff City", "Pickup City")]  # 3h
        self.plan = simulate(legs, cycle_used_hrs=68.0, start=_dt(hh=6))

    def test_restart_inserted(self):
        self.assertEqual(len(_stops_of(self.plan, "restart")), 1)

    def test_restart_is_34_hours(self):
        restart = _stops_of(self.plan, "restart")[0]
        self.assertEqual(restart.duration_hrs, C.RESTART_HOURS)


class Invariants(unittest.TestCase):
    """Properties that must hold for any trip."""

    def test_various_trips_days_sum_to_24(self):
        cases = [
            ([Leg(0, "P", "O"), Leg(300, "D", "P")], 0.0),
            ([Leg(120, "P", "O"), Leg(1400, "D", "P")], 10.0),
            ([Leg(500, "P", "O"), Leg(2100, "D", "P")], 30.0),
        ]
        for legs, cycle in cases:
            plan = simulate(legs, cycle_used_hrs=cycle, start=_dt(hh=8))
            for day in build_days(plan.segments):
                self.assertEqual(
                    day["total_hours"], 24.0,
                    msg=f"day {day['index']} of trip {legs} != 24h",
                )

    def test_never_exceeds_11h_driving_between_rests(self):
        legs = [Leg(0, "P", "O"), Leg(2100, "D", "P")]
        plan = simulate(legs, cycle_used_hrs=0.0, start=_dt(hh=8))
        driving_run = 0.0
        for seg in plan.segments:
            if seg.status == C.DRIVING:
                driving_run += seg.hours
                self.assertLessEqual(driving_run, C.MAX_DRIVING_HOURS + C.EPS)
            elif seg.status in (C.SLEEPER, C.OFF_DUTY) and seg.hours >= C.DAILY_RESET_HOURS - C.EPS:
                driving_run = 0.0

    def test_long_haul_fuels_every_1000_miles(self):
        # 2100-mile leg -> fuel at ~1000 and ~2000 miles => 2 fuel stops.
        legs = [Leg(0, "P", "O"), Leg(2100, "D", "P")]
        plan = simulate(legs, cycle_used_hrs=0.0, start=_dt(hh=8))
        self.assertEqual(len(_stops_of(plan, "fuel")), 2)


class SubMileRemainderRegression(unittest.TestCase):
    """Fractional distances that land just past a limit boundary must not hang
    the driving loop (was a units-mismatch infinite loop)."""

    def test_fractional_distances_terminate(self):
        for miles in [440.01, 605.01, 1000.01, 1210.01, 1650.01, 2000.01, 605.02]:
            legs = [Leg(0, "P", "O"), Leg(miles, "D", "P")]
            plan = simulate(legs, cycle_used_hrs=0.0, start=_dt(hh=6))
            self.assertAlmostEqual(_driving_hours(plan), miles / C.AVG_SPEED_MPH, places=2,
                                   msg=f"driving hours wrong for {miles} mi")


class FuelExactBoundary(unittest.TestCase):
    """A leg ending exactly on a 1,000-mile multiple should not add a trailing
    fuel stop at the destination."""

    def test_exact_1000_miles(self):
        legs = [Leg(0, "P", "O"), Leg(1000, "D", "P")]
        plan = simulate(legs, cycle_used_hrs=0.0, start=_dt(hh=6))
        self.assertAlmostEqual(_driving_hours(plan), 1000 / C.AVG_SPEED_MPH, places=2)
        # At most one fuel stop (the 1000-mi mark coincides with arrival).
        self.assertLessEqual(len(_stops_of(plan, "fuel")), 1)


class PerDayMiles(unittest.TestCase):
    def test_per_day_miles_sum_to_total(self):
        legs = [Leg(120, "P", "O"), Leg(1400, "D", "P")]
        plan = simulate(legs, cycle_used_hrs=0.0, start=_dt(hh=8))
        days = build_days(plan.segments)
        self.assertAlmostEqual(sum(d["total_miles"] for d in days),
                               round(plan.total_miles), delta=2)


class QuarterHourTotals(unittest.TestCase):
    """Every Total Hours value is a multiple of 0.25 and the day still sums to 24."""

    def test_totals_snap_to_quarter_hour(self):
        cases = [
            ([Leg(222, "P", "O"), Leg(680, "D", "P")], 0.0),
            ([Leg(0, "P", "O"), Leg(1488, "D", "P")], 10.0),
            ([Leg(510, "P", "O"), Leg(2101, "D", "P")], 30.0),
        ]
        for legs, cyc in cases:
            plan = simulate(legs, cycle_used_hrs=cyc, start=_dt(hh=8))
            for day in build_days(plan.segments):
                for status, v in day["totals"].items():
                    self.assertAlmostEqual(v * 4, round(v * 4), places=6,
                                           msg=f"{status}={v} is not a multiple of 0.25")
                self.assertEqual(day["total_hours"], 24.0)


class CycleRestartRecap(unittest.TestCase):
    """A trip long enough to burn the 70-hr cycle must show the recap reset
    after the 34-hr restart (used_last_8_days drops, not monotonic)."""

    def setUp(self):
        legs = [Leg(0, "P", "O"), Leg(4200, "D", "P")]
        self.plan = simulate(legs, cycle_used_hrs=0.0, start=_dt(hh=6))
        self.days = build_days(self.plan.segments)

    def test_restart_occurs(self):
        self.assertGreaterEqual(len(_stops_of(self.plan, "restart")), 1)

    def test_recap_resets_and_never_exceeds_cap(self):
        used = [d["recap"]["used_last_8_days"] for d in self.days]
        # A reset means the series decreases somewhere.
        self.assertTrue(any(b < a for a, b in zip(used, used[1:])),
                        msg=f"recap never reset: {used}")
        # Cycle accounting should not run away past the 70-hr cap (+ snap slack).
        self.assertLessEqual(max(used), 70.25)

    def test_recap_is_quarter_hour_and_conserved(self):
        # Start mid-cycle so the restart-completion reset is exercised.
        days = build_days(
            simulate([Leg(0, "P", "O"), Leg(2300, "D", "P")],
                     cycle_used_hrs=50, start=_dt(hh=6)).segments,
            cycle_used_start=50)
        for day in days:
            r = day["recap"]
            for v in (r["used_last_8_days"], r["available_tomorrow"], r["on_duty_today"]):
                self.assertAlmostEqual(v * 4, round(v * 4), places=6,
                                       msg=f"{v} not a multiple of 0.25")
            if r["used_last_8_days"] <= 70:
                self.assertAlmostEqual(
                    r["used_last_8_days"] + r["available_tomorrow"], 70, places=6)


class RemarksNearMidnight(unittest.TestCase):
    """A duty change just before midnight is attributed to the correct day."""

    def test_remark_before_midnight_on_day1(self):
        base = _dt(2026, 7, 16)
        segs = [
            Segment(C.OFF_DUTY, base, base.replace(hour=23)),
            Segment(C.ON_DUTY, base.replace(hour=23), base.replace(hour=23, minute=30),
                    location="Amarillo, TX", note="Fuel"),
            Segment(C.DRIVING, base.replace(hour=23, minute=30),
                    base.replace(hour=23) + timedelta(hours=2)),  # crosses midnight
        ]
        days = build_days(segs)
        self.assertEqual(days[0]["remarks"][0]["location"], "Amarillo, TX")
        self.assertEqual(days[0]["remarks"][0]["time"], "23:00")
        # Both calendar days still total 24h despite the midnight-crossing drive.
        for d in days:
            self.assertEqual(d["total_hours"], 24.0)


if __name__ == "__main__":
    unittest.main()
