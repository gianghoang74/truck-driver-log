"""Rate limiting for the public, unauthenticated API.

Two layers protect the OpenRouteService quota:

* **Per-IP** throttles (``PlanRateThrottle`` / ``GeocodeRateThrottle``) give every
  client its own bucket. They stop a single abuser but do *not* bound the total
  across many distinct clients — 12 users under their individual limit can still
  sum past the ORS quota.

* A **global** throttle (``GlobalORSThrottle``) puts *every* caller in one shared
  bucket, so it caps aggregate traffic to the ORS-backed endpoints regardless of
  how many IPs are calling. Sized below ORS's own per-minute limit so we return a
  429 before ORS starts rejecting us (which would otherwise surface as 502s).

Rates live in ``settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`` and are
env-tunable. Throttles are applied per-view (see ``api/views.py``), not globally,
so ``/health/`` stays unlimited for the keep-alive ping.

Note: throttle counters use Django's cache (LocMemCache here), which is
per-process. With a single gunicorn worker that is effectively one shared
counter; if scaled to multiple workers/instances, point the cache at Redis so
the counters are shared.
"""

from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class PlanRateThrottle(AnonRateThrottle):
    """Per-IP limit on trip planning (the ORS *directions* consumer)."""

    scope = "plan"


class GeocodeRateThrottle(AnonRateThrottle):
    """Per-IP limit on the autocomplete/geocode proxy."""

    scope = "geocode"


class GlobalORSThrottle(SimpleRateThrottle):
    """App-wide ceiling shared by *every* client on the ORS-consuming endpoints.

    All requests hash to the same bucket, so this bounds total ORS traffic no
    matter how many distinct IPs are calling — the gap per-IP throttles leave.
    """

    scope = "global_ors"

    def get_cache_key(self, request, view):
        return "throttle_global_ors"  # constant key => single shared bucket
