from rest_framework import serializers
from apps.bookings.models import Booking


class BookingSerializer(serializers.ModelSerializer):
    booked_by_name = serializers.CharField(source="booked_by.get_full_name", read_only=True)
    asset_tag      = serializers.CharField(source="asset.asset_tag", read_only=True)
    asset_name     = serializers.CharField(source="asset.name", read_only=True)

    class Meta:
        model  = Booking
        fields = [
            "id", "asset", "asset_tag", "asset_name",
            "booked_by", "booked_by_name",
            "start_time", "end_time", "purpose", "status",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "booked_by", "status", "created_at", "updated_at"]

    def validate(self, attrs):
        start = attrs.get("start_time") or (self.instance.start_time if self.instance else None)
        end   = attrs.get("end_time")   or (self.instance.end_time   if self.instance else None)
        asset = attrs.get("asset")      or (self.instance.asset      if self.instance else None)

        if start and end and start >= end:
            raise serializers.ValidationError(
                {"end_time": "end_time must be after start_time."}
            )

        if start and end and asset:
            # Overlap rule: reject if new_start < existing_end AND new_end > existing_start
            # Exact back-to-back (new_start == existing_end) is allowed
            qs = Booking.objects.filter(
                asset=asset,
                status__in=(Booking.Status.CONFIRMED, Booking.Status.PENDING),
                start_time__lt=end,   # existing_start < new_end
                end_time__gt=start,   # existing_end > new_start (strict — back-to-back OK)
            ).exclude(pk=self.instance.pk if self.instance else None)

            conflict = qs.first()
            if conflict:
                raise serializers.ValidationError(
                    {
                        "non_field_errors": (
                            f"Booking conflicts with an existing booking "
                            f"({conflict.start_time.isoformat()} – {conflict.end_time.isoformat()})."
                        ),
                        "conflicting_booking": {
                            "id": str(conflict.id),
                            "start_time": conflict.start_time.isoformat(),
                            "end_time":   conflict.end_time.isoformat(),
                        },
                    }
                )
        return attrs


class BookingRescheduleSerializer(serializers.Serializer):
    start_time = serializers.DateTimeField()
    end_time   = serializers.DateTimeField()

    def validate(self, attrs):
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError({"end_time": "end_time must be after start_time."})
        return attrs
