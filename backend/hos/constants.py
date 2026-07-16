"""Hours-of-Service constants and modeling assumptions.

All rules are for a property-carrying driver on the 70-hour / 8-day cycle,
following the FMCSA Hours-of-Service regulations (49 CFR Part 395).

These are the single source of truth for the engine; keep them here so they
can be tuned and surfaced in the UI.
"""

# --- Duty statuses (the four ELD grid rows) ---
OFF_DUTY = "off_duty"
SLEEPER = "sleeper"
DRIVING = "driving"
ON_DUTY = "on_duty"  # on duty, not driving

DUTY_STATUSES = (OFF_DUTY, SLEEPER, DRIVING, ON_DUTY)

# --- HOS limits (hours) ---
MAX_DRIVING_HOURS = 11.0        # 11-hour driving limit
MAX_WINDOW_HOURS = 14.0         # 14-hour on-duty "driving window"
DRIVING_BEFORE_BREAK = 8.0      # 30-min break required after 8 cumulative driving hrs
MIN_BREAK_HOURS = 0.5           # any >=30-min non-driving period satisfies the break (p.10)
DAILY_RESET_HOURS = 10.0        # 10 consecutive hrs off duty resets the 11/14-hr clocks
CYCLE_HOURS = 70.0              # 70 on-duty hrs in a rolling 8-day window
CYCLE_DAYS = 8
RESTART_HOURS = 34.0            # 34+ consecutive hrs off duty resets the cycle

# --- Modeling assumptions ---
AVG_SPEED_MPH = 55.0            # average driving speed
FUEL_INTERVAL_MILES = 1000.0   # fuel at least once every 1,000 miles
FUEL_DURATION_HOURS = 0.5      # on-duty (not driving) time per fueling
PICKUP_HOURS = 1.0             # 1 hr on duty for pickup
DROPOFF_HOURS = 1.0           # 1 hr on duty for dropoff

# Numeric tolerance for float comparisons (hours). ~1.8 seconds.
EPS = 5e-4

# Distance tolerance (miles) consistent with EPS hours, so the driving loop's
# distance guard and its hours-based "effectively zero" test agree.
MILE_EPS = EPS * AVG_SPEED_MPH
