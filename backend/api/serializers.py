import math

from rest_framework import serializers


def finite(value):
    """Reject NaN/inf, which slip past min/max validators (all NaN comparisons
    are False) and later crash the strict JSON renderer."""
    if not math.isfinite(value):
        raise serializers.ValidationError("Must be a finite number.")
    return value


class PlanInputSerializer(serializers.Serializer):
    current_location = serializers.CharField(max_length=255)
    pickup_location = serializers.CharField(max_length=255)
    dropoff_location = serializers.CharField(max_length=255)
    current_cycle_used_hrs = serializers.FloatField(
        min_value=0, max_value=70, validators=[finite]
    )
