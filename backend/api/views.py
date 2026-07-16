from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

import routing
from routing import RoutingError, RoutingNotConfigured

from .planner import plan_trip
from .serializers import PlanInputSerializer


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


@api_view(["POST"])
def plan(request):
    """Plan a trip: geocode + route + HOS logs, return the payload (stateless)."""
    serializer = PlanInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        result = plan_trip(
            current=data["current_location"],
            pickup=data["pickup_location"],
            dropoff=data["dropoff_location"],
            cycle_used_hrs=data["current_cycle_used_hrs"],
        )
    except RoutingNotConfigured as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except RoutingError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    return Response(result)


@api_view(["GET"])
def geocode_autocomplete(request):
    """Type-ahead proxy for the location inputs."""
    text = request.query_params.get("text", "").strip()
    if len(text) < 3:
        return Response({"suggestions": []})
    try:
        suggestions = routing.autocomplete(text)
    except RoutingNotConfigured as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except RoutingError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    return Response({"suggestions": suggestions})
