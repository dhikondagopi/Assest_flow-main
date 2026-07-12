from rest_framework import serializers
from apps.maintenance.models import MaintenanceRequest


class MaintenanceRequestSerializer(serializers.ModelSerializer):
    asset_tag          = serializers.CharField(source="asset.asset_tag",            read_only=True)
    asset_name         = serializers.CharField(source="asset.name",                 read_only=True)
    requested_by_name  = serializers.CharField(source="requested_by.get_full_name", read_only=True)
    assigned_to_name   = serializers.CharField(source="assigned_to.get_full_name",  read_only=True)

    class Meta:
        model  = MaintenanceRequest
        fields = [
            "id", "asset", "asset_tag", "asset_name",
            "requested_by", "requested_by_name",
            "assigned_to", "assigned_to_name",
            "status", "priority", "description",
            "resolution_notes", "scheduled_date",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "requested_by", "status", "created_at", "updated_at"
        ]


class MaintenanceStatusUpdateSerializer(serializers.Serializer):
    """Used by approve / in-progress / resolve / reject actions."""
    # Assumption: resolution_notes required only for RESOLVED transition
    resolution_notes = serializers.CharField(required=False, allow_blank=True)
    assigned_to      = serializers.UUIDField(required=False, allow_null=True)
    scheduled_date   = serializers.DateField(required=False, allow_null=True)
