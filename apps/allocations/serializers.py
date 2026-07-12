from rest_framework import serializers
from apps.allocations.models import Allocation, TransferRequest


class AllocationSerializer(serializers.ModelSerializer):
    asset_tag         = serializers.CharField(source="asset.asset_tag", read_only=True)
    asset_name        = serializers.CharField(source="asset.name", read_only=True)
    employee_name     = serializers.CharField(source="employee.user.get_full_name", read_only=True)
    allocated_by_name = serializers.CharField(source="allocated_by.get_full_name", read_only=True)

    class Meta:
        model  = Allocation
        fields = [
            "id", "asset", "asset_tag", "asset_name",
            "employee", "employee_name",
            "allocated_by", "allocated_by_name",
            "status", "allocated_at", "due_date", "returned_at", "notes",
        ]
        read_only_fields = [
            "id", "status", "allocated_at", "returned_at",
            "allocated_by",
        ]

    def validate(self, attrs):
        from apps.assets.models import Asset
        asset = attrs.get("asset") or (self.instance.asset if self.instance else None)
        if self.instance is None:  # creation only
            if asset and asset.status != Asset.Status.AVAILABLE:
                # Check for active allocation
                active = Allocation.objects.filter(
                    asset=asset, status=Allocation.Status.ACTIVE
                ).select_related("employee__user").first()
                if active:
                    raise serializers.ValidationError(
                        {
                            "asset": (
                                f"Currently held by {active.employee.user.get_full_name()}. "
                                "Use transfer request instead."
                            ),
                            "current_holder_id": str(active.employee.user.id),
                        }
                    )
                raise serializers.ValidationError(
                    {"asset": f"Asset is not available (status: {asset.status})."}
                )
        return attrs


class TransferRequestSerializer(serializers.ModelSerializer):
    asset_tag            = serializers.CharField(source="asset.asset_tag", read_only=True)
    from_employee_name   = serializers.CharField(
        source="from_employee.user.get_full_name", read_only=True
    )
    to_employee_name     = serializers.CharField(
        source="to_employee.user.get_full_name", read_only=True
    )
    requested_by_name    = serializers.CharField(
        source="requested_by.get_full_name", read_only=True
    )

    class Meta:
        model  = TransferRequest
        fields = [
            "id", "asset", "asset_tag",
            "from_employee", "from_employee_name",
            "to_employee", "to_employee_name",
            "requested_by", "requested_by_name",
            "approved_by", "status", "reason",
            "created_at", "resolved_at",
        ]
        read_only_fields = [
            "id", "status", "requested_by",
            "approved_by", "created_at", "resolved_at",
        ]

    def validate(self, attrs):
        from_emp = attrs.get("from_employee")
        to_emp   = attrs.get("to_employee")
        asset    = attrs.get("asset")
        if from_emp and to_emp and from_emp == to_emp:
            raise serializers.ValidationError(
                {"to_employee": "Transfer target must be different from current holder."}
            )
        if asset and from_emp:
            active = Allocation.objects.filter(
                asset=asset,
                employee=from_emp,
                status=Allocation.Status.ACTIVE,
            ).first()
            if not active:
                raise serializers.ValidationError(
                    {"from_employee": "No active allocation found for this employee and asset."}
                )
        return attrs
