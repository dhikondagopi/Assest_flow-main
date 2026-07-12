from rest_framework import serializers
from apps.assets.models import Asset


class AssetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model  = Asset
        fields = [
            "id", "asset_tag", "name", "description",
            "category", "category_name", "status",
            "qr_code_value", "serial_number",
            "purchase_date", "purchase_cost", "location",
            "extra_data", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "asset_tag", "qr_code_value", "created_at", "updated_at"]

    def validate_status(self, value):
        # Prevent direct manual set to UNDER_MAINTENANCE/ALLOCATED via this endpoint
        # Assumption: status changes driven by allocation/maintenance workflows
        restricted = {Asset.Status.UNDER_MAINTENANCE, Asset.Status.ALLOCATED}
        instance = getattr(self, "instance", None)
        if instance and value in restricted and instance.status not in restricted:
            raise serializers.ValidationError(
                f"Status '{value}' is managed automatically by allocation/maintenance workflows."
            )
        return value


class AssetListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model  = Asset
        fields = [
            "id", "asset_tag", "name", "category_name",
            "status", "location", "qr_code_value",
        ]
