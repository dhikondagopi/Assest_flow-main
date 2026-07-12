from django.contrib.auth import get_user_model
from rest_framework import serializers
from apps.org.models import AssetCategory, Department, EmployeeProfile

User = get_user_model()


# ── Department ────────────────────────────────────────────────────────────────

class DepartmentSerializer(serializers.ModelSerializer):
    children_count = serializers.SerializerMethodField()

    class Meta:
        model  = Department
        fields = [
            "id", "name", "code", "parent", "head",
            "description", "children_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_children_count(self, obj):
        return obj.children.count()

    def validate_parent(self, value):
        if value and self.instance and value.pk == self.instance.pk:
            raise serializers.ValidationError("A department cannot be its own parent.")
        return value


class DepartmentTreeSerializer(DepartmentSerializer):
    """Recursive nested representation for tree view."""
    children = serializers.SerializerMethodField()

    class Meta(DepartmentSerializer.Meta):
        fields = DepartmentSerializer.Meta.fields + ["children"]

    def get_children(self, obj):
        return DepartmentTreeSerializer(obj.children.all(), many=True).data


# ── AssetCategory ─────────────────────────────────────────────────────────────

class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = AssetCategory
        fields = ["id", "name", "description", "extra_fields", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_extra_fields(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("extra_fields must be a JSON array.")
        for item in value:
            if not isinstance(item, dict) or "name" not in item:
                raise serializers.ValidationError(
                    'Each extra_field must be an object with at least a "name" key.'
                )
        return value


# ── EmployeeProfile ────────────────────────────────────────────────────────────

class EmployeeProfileSerializer(serializers.ModelSerializer):
    user_email      = serializers.EmailField(source="user.email", read_only=True)
    user_full_name  = serializers.CharField(source="user.get_full_name", read_only=True)
    role            = serializers.CharField(source="user.role", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model  = EmployeeProfile
        fields = [
            "id", "user", "user_email", "user_full_name", "role",
            "department", "department_name", "employee_number", "phone",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]
