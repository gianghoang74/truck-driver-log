"""Pure-Python Hours-of-Service trip simulator.

No Django/framework dependencies — this is the graded accuracy core and is
exercised directly by unit tests. Given the driving legs of a trip and the
cycle hours already used, it produces:

  * a flat list of duty-status ``Segment``s over an absolute timeline,
  * the notable ``Stop``s (pickup, dropoff, fuel, rest, restart) for the map,
  * per-day log data (status totals that sum to 24h, remarks, recap).

The simulation advances a virtual clock, inserting fuel stops, 30-minute
breaks, 10-hour resets and 34-hour restarts exactly when the HOS limits
require them. See ``constants.py`` for the rules and their FMCSA citations.

v1 simplification: the 70-hour cycle is tracked as a single accumulating
counter (not a true per-day rolling window) and rest is modeled as a full
10-hour reset — the split-sleeper-berth provision is deferred. Both keep the
output strictly legal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Optional

from . import constants as C


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class Leg:
    """One driving leg of the trip."""
    miles: float
    to_label: str          # destination place name (for remarks/map)
    from_label: str = ""   # origin place name (used for the trip's first remark)


@dataclass
class Segment:
    """A continuous period in one duty status."""
    status: str
    start: datetime
    end: datetime
    location: Optional[str] = None
    note: Optional[str] = None

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600.0


@dataclass
class Stop:
    """A notable non-driving event, surfaced on the map/summary."""
    type: str              # pickup | dropoff | fuel | break | rest | restart
    start: datetime
    duration_hrs: float
    mile: float = 0.0                 # cumulative trip miles when the stop occurs
    label: Optional[str] = None       # e.g. "mile 1000"
    location: Optional[str] = None
    satisfies_break: bool = False     # did this reset the 8-hr driving clock?


@dataclass
class TripPlan:
    segments: list[Segment] = field(default_factory=list)
    stops: list[Stop] = field(default_factory=list)
    total_miles: float = 0.0


# --------------------------------------------------------------------------- #
# Simulator
# --------------------------------------------------------------------------- #
class TripSimulator:
    """Advances the HOS clock over a sequence of driving legs."""

    def __init__(self, start: datetime, cycle_used_hrs: float = 0.0):
        self.now = start
        self.cycle_used = cycle_used_hrs
        self.plan = TripPlan()

        # Daily clocks (reset by a 10-hr rest / 34-hr restart).
        self.driving_today = 0.0            # hrs driven in the current 11-hr limit
        self.driving_since_break = 0.0      # hrs driven since last >=30-min non-driving
        self.window_start = start           # start of the current 14-hr window

        # Fueling tracker.
        self.miles_total = 0.0
        self.next_fuel = C.FUEL_INTERVAL_MILES

    # -- low-level segment emission ---------------------------------------- #
    def _emit(self, status: str, hours: float, location=None, note=None) -> None:
        if hours <= 0:
            return
        end = self.now + timedelta(hours=hours)
        self.plan.segments.append(Segment(status, self.now, end, location, note))

        if status == C.DRIVING:
            self.driving_today += hours
            self.driving_since_break += hours
            self.cycle_used += hours
        elif status == C.ON_DUTY:
            self.cycle_used += hours
            if hours >= C.MIN_BREAK_HOURS:      # counts as a qualifying break
                self.driving_since_break = 0.0
        else:  # OFF_DUTY or SLEEPER
            if hours >= C.MIN_BREAK_HOURS:
                self.driving_since_break = 0.0
        self.now = end

    def _window_left(self) -> float:
        used = (self.now - self.window_start).total_seconds() / 3600.0
        return C.MAX_WINDOW_HOURS - used

    # -- inserted events --------------------------------------------------- #
    def _rest(self) -> None:
        self.plan.stops.append(
            Stop("rest", self.now, C.DAILY_RESET_HOURS, mile=self.miles_total,
                 satisfies_break=True)
        )
        self._emit(C.SLEEPER, C.DAILY_RESET_HOURS, note="10-hour rest")
        self.driving_today = 0.0
        self.driving_since_break = 0.0
        self.window_start = self.now  # new window begins at end of rest

    def _restart(self) -> None:
        self.plan.stops.append(
            Stop("restart", self.now, C.RESTART_HOURS, mile=self.miles_total,
                 satisfies_break=True)
        )
        self._emit(C.OFF_DUTY, C.RESTART_HOURS, note="34-hour restart")
        self.cycle_used = 0.0
        self.driving_today = 0.0
        self.driving_since_break = 0.0
        self.window_start = self.now

    def _fuel(self) -> None:
        label = f"mile {int(round(self.miles_total))}"
        self.plan.stops.append(
            Stop("fuel", self.now, C.FUEL_DURATION_HOURS, mile=self.miles_total,
                 label=label, satisfies_break=True)
        )
        self._emit(C.ON_DUTY, C.FUEL_DURATION_HOURS, location=label, note="Fuel stop")
        self.next_fuel += C.FUEL_INTERVAL_MILES

    def _break(self) -> None:
        self.plan.stops.append(
            Stop("break", self.now, C.MIN_BREAK_HOURS, mile=self.miles_total,
                 satisfies_break=True)
        )
        self._emit(C.OFF_DUTY, C.MIN_BREAK_HOURS, note="30-minute break")

    def _on_duty(self, hours: float, type_: str, label: str) -> None:
        self.plan.stops.append(
            Stop(type_, self.now, hours, mile=self.miles_total, label=label,
                 location=label, satisfies_break=hours >= C.MIN_BREAK_HOURS)
        )
        self._emit(C.ON_DUTY, hours, location=label, note=type_.capitalize())

    # -- driving ----------------------------------------------------------- #
    def _ensure_drivable(self) -> None:
        """Insert a restart/rest if a limit blocks driving *before* we start."""
        if self.cycle_used >= C.CYCLE_HOURS - C.EPS:
            self._restart()
        if (self.driving_today >= C.MAX_DRIVING_HOURS - C.EPS
                or self._window_left() <= C.EPS):
            self._rest()

    def drive(self, miles: float, dest_label: str, origin_label: str = "") -> None:
        # `remaining` is in miles; compare it against MILE_EPS (not the hours
        # tolerance EPS) so the loop guard and the hours-based chunk test agree
        # on "effectively arrived" — otherwise a sub-mile remainder can spin.
        remaining = miles
        first_chunk = True
        while remaining > C.MILE_EPS:
            self._ensure_drivable()

            by_dist = remaining / C.AVG_SPEED_MPH
            by_daily = C.MAX_DRIVING_HOURS - self.driving_today
            by_window = self._window_left()
            by_break = C.DRIVING_BEFORE_BREAK - self.driving_since_break
            by_fuel = (self.next_fuel - self.miles_total) / C.AVG_SPEED_MPH
            by_cycle = C.CYCLE_HOURS - self.cycle_used
            chunk = min(by_dist, by_daily, by_window, by_break, by_fuel, by_cycle)

            if chunk <= C.EPS:
                # A binding limit is exactly at zero. Distance-done is terminal;
                # break/fuel are handled here; daily/window/cycle by _ensure_drivable.
                if by_dist <= C.EPS:
                    break
                if by_break <= C.EPS:
                    self._break()
                elif by_fuel <= C.EPS:
                    self._fuel()
                else:
                    self._ensure_drivable()
                continue

            note = "Start driving" if first_chunk else None
            loc = origin_label if first_chunk else None
            self._emit(C.DRIVING, chunk, location=loc, note=note)
            first_chunk = False

            driven = chunk * C.AVG_SPEED_MPH
            remaining -= driven
            self.miles_total += driven
            self.plan.total_miles += driven

            if remaining <= C.MILE_EPS:
                break

            # React to whichever limit the chunk just hit.
            if self.miles_total >= self.next_fuel - C.EPS:
                self._fuel()
            elif self.driving_since_break >= C.DRIVING_BEFORE_BREAK - C.EPS:
                # Skip a dedicated break if a 10-hr rest is already forced — the
                # rest satisfies the break, so an extra 30-min stop is spurious.
                rest_imminent = (self.driving_today >= C.MAX_DRIVING_HOURS - C.EPS
                                 or self._window_left() <= C.EPS
                                 or self.cycle_used >= C.CYCLE_HOURS - C.EPS)
                if not rest_imminent:
                    self._break()
            # daily / window / cycle limits are resolved at the next loop top.


# --------------------------------------------------------------------------- #
# Top-level entry points
# --------------------------------------------------------------------------- #
def simulate(legs: list[Leg], cycle_used_hrs: float, start: datetime) -> TripPlan:
    """Run the full trip: drive to pickup, load, drive to dropoff, unload."""
    if len(legs) != 2:
        raise ValueError("expected exactly two legs: [current->pickup, pickup->dropoff]")

    sim = TripSimulator(start, cycle_used_hrs)
    pickup, delivery = legs

    sim.drive(pickup.miles, pickup.to_label, origin_label=pickup.from_label)
    sim._on_duty(C.PICKUP_HOURS, "pickup", pickup.to_label)
    sim.drive(delivery.miles, delivery.to_label, origin_label=delivery.from_label)
    sim._on_duty(C.DROPOFF_HOURS, "dropoff", delivery.to_label)

    return sim.plan


def _split_at_midnight(segments: list[Segment]) -> list[Segment]:
    """Split any segment that crosses midnight so each piece is within one day."""
    out: list[Segment] = []
    for seg in segments:
        start = seg.start
        while seg.end.date() > start.date():
            midnight = datetime.combine(start.date() + timedelta(days=1), time.min,
                                        tzinfo=start.tzinfo)
            out.append(Segment(seg.status, start, midnight, seg.location, seg.note))
            start = midnight
        if start < seg.end:  # skip a zero-length tail when a segment ends at midnight
            out.append(Segment(seg.status, start, seg.end, seg.location, seg.note))
    return out


_QUARTER_MIN = 15


def _snap_quarter_hour(segs: list[Segment], day_start: datetime,
                       day_end: datetime) -> list[Segment]:
    """Snap contiguous day segments to a 15-minute grid.

    Paper ELD logs have quarter-hour resolution, so every duty-status total
    should be a multiple of 0.25h. Snapping the transition times keeps the
    segments contiguous and still covering the full 24h (they sum to 24).
    """
    if not segs:
        return segs
    total_min = round((day_end - day_start).total_seconds() / 60)  # 1440
    out: list[Segment] = []
    prev = 0
    last = len(segs) - 1
    for i, seg in enumerate(segs):
        if i == last:
            end = total_min  # the final segment always closes out the day
        else:
            raw_end = (seg.end - day_start).total_seconds() / 60
            end = round(raw_end / _QUARTER_MIN) * _QUARTER_MIN
        end = max(prev, min(end, total_min))
        if end > prev:
            out.append(Segment(seg.status,
                               day_start + timedelta(minutes=prev),
                               day_start + timedelta(minutes=end),
                               seg.location, seg.note))
        prev = end
    return out


def _restart_end_dates(segments: list[Segment]) -> set:
    """Calendar dates on which a 34-hr restart *completes*.

    A restart resets the 70-hr cycle only when it finishes, so the recap resets
    on the day the restart ends — not the day it begins.
    """
    return {
        seg.end.date() for seg in segments
        if seg.status in (C.OFF_DUTY, C.SLEEPER) and seg.hours >= C.RESTART_HOURS - C.EPS
    }


def build_days(segments: list[Segment], cycle_used_start: float = 0.0) -> list[dict]:
    """Group segments into per-calendar-day logs with totals, remarks and recap.

    Pure and independently testable: feed it any segment list (e.g. the FMCSA
    "John Doe" example) and it returns the per-day breakdown.
    """
    if not segments:
        return []

    pieces = _split_at_midnight(segments)
    tzinfo = segments[0].start.tzinfo

    # Odometer miles per day come from the real (unsnapped) driving time, so the
    # "Total Miles Driving Today" stays exact even though the grid is rounded.
    miles_by_date: dict = {}
    for seg in pieces:
        if seg.status == C.DRIVING:
            miles_by_date[seg.start.date()] = (
                miles_by_date.get(seg.start.date(), 0.0) + seg.hours * C.AVG_SPEED_MPH)

    # Group day -> segments (preserving order).
    by_date: dict = {}
    for seg in pieces:
        by_date.setdefault(seg.start.date(), []).append(seg)

    # Fill uncovered time in each day with Off Duty so every log covers the
    # full 24h (before the driver comes on duty, after dropoff, etc.).
    for date, segs in by_date.items():
        segs.sort(key=lambda s: s.start)
        day_start = datetime.combine(date, time.min, tzinfo=tzinfo)
        day_end = day_start + timedelta(days=1)
        filled: list[Segment] = []
        cursor = day_start
        for seg in segs:
            if seg.start > cursor:
                filled.append(Segment(C.OFF_DUTY, cursor, seg.start))
            filled.append(seg)
            cursor = seg.end
        if cursor < day_end:
            filled.append(Segment(C.OFF_DUTY, cursor, day_end))
        # Snap to the 15-min grid so totals are quarter-hour and still sum to 24.
        by_date[date] = _snap_quarter_hour(filled, day_start, day_end)

    # Remarks come from the *original* segments (avoid duplicate midnight splits):
    # any segment carrying a location or note marks a duty change worth noting.
    remarks_by_date: dict = {}
    for seg in segments:
        if seg.location or seg.note:
            remarks_by_date.setdefault(seg.start.date(), []).append({
                "time": seg.start.strftime("%H:%M"),
                "location": seg.location,
                "note": seg.note,
            })

    restart_end_dates = _restart_end_dates(segments)

    days: list[dict] = []
    cycle_used = cycle_used_start
    for idx, date in enumerate(sorted(by_date), start=1):
        segs = by_date[date]
        totals = {s: 0.0 for s in C.DUTY_STATUSES}
        on_duty_today = 0.0
        for seg in segs:
            h = seg.hours
            totals[seg.status] += h
            if seg.status in (C.DRIVING, C.ON_DUTY):
                on_duty_today += h

        totals = {k: round(v, 2) for k, v in totals.items()}
        total_miles = round(miles_by_date.get(date, 0.0))
        # Recap runs off the snapped per-day on-duty (quarter-hour, matches the
        # grid); a restart that completes today zeroes the cycle first.
        if date in restart_end_dates:
            cycle_used = 0.0
        cycle_used += on_duty_today
        recap = {
            "on_duty_today": round(on_duty_today, 2),
            "used_last_8_days": round(cycle_used, 2),
            "available_tomorrow": round(max(C.CYCLE_HOURS - cycle_used, 0.0), 2),
        }

        days.append({
            "index": idx,
            "date": date.isoformat(),
            "total_miles": total_miles,
            "segments": [
                {
                    "status": s.status,
                    "start": s.start.strftime("%H:%M"),
                    "end": s.end.strftime("%H:%M") if s.end.time() != time.min
                    else "24:00",
                    "location": s.location,
                    "note": s.note,
                }
                for s in segs
            ],
            "totals": totals,
            "total_hours": round(sum(totals.values()), 2),
            "remarks": remarks_by_date.get(date, []),
            "recap": recap,
        })
    return days
