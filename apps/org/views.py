from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdmin, IsAdminOrAssetManager
from apps.org.models import AssetCategory, Department, EmployeeProfile
from apps.org.serializers import (
    AssetCategorySerializer,
    DepartmentSerializer,
    DepartmentTreeSerializer,
    EmployeeProfileSerializer,
)


# ── Department ────────────────────────────────────────────────────────────────

class DepartmentListCreateView(generics.ListCreateAPIView):
    """GET (all) / POST (admin only)."""
    queryset         = Department.objects.select_related("parent", "head").prefetch_related("children")
    serializer_class = DepartmentSerializer
    search_fields    = ["name", "code"]
    ordering_fields  = ["name", "created_at"]

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdmin()]


class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET (all) / PUT/PATCH/DELETE (admin only)."""
    queryset         = Department.objects.all()
    serializer_class = DepartmentSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdmin()]


class DepartmentTreeView(APIView):
    """GET /api/org/departments/tree/ — hierarchical tree, authenticated."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        roots = Department.objects.filter(parent__isnull=True)
        return Response(DepartmentTreeSerializer(roots, many=True).data)


# ── AssetCategory ─────────────────────────────────────────────────────────────

class AssetCategoryListCreateView(generics.ListCreateAPIView):
    queryset         = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer
    search_fields    = ["name"]
    ordering_fields  = ["name", "created_at"]

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdmin()]


class AssetCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset         = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdmin()]


# ── EmployeeProfile ───────────────────────────────────────────────────────────

class EmployeeProfileListView(generics.ListAPIView):
    """GET /api/org/employees/ — Admin sees all; Dept Head sees own dept."""
    serializer_class = EmployeeProfileSerializer
    search_fields    = ["user__email", "user__first_name", "user__last_name", "employee_number"]
    ordering_fields  = ["user__first_name", "created_at"]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs   = EmployeeProfile.objects.select_related("user", "department")
        if user.role in ("ADMIN", "ASSET_MANAGER"):
            return qs
        if user.role == "DEPARTMENT_HEAD":
            # Dept head sees only own department members
            try:
                dept = user.profile.department
            except EmployeeProfile.DoesNotExist:
                return qs.none()
            return qs.filter(department=dept)
        # Regular employees see only themselves
        return qs.filter(user=user)


class EmployeeProfileDetailView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/org/employees/<id>/ — Admin full; others own profile."""
    serializer_class = EmployeeProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs   = EmployeeProfile.objects.select_related("user", "department")
        if user.role in ("ADMIN", "ASSET_MANAGER"):
            return qs
        return qs.filter(user=user)

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH") and self.request.user.role not in ("ADMIN",):
            from rest_framework.permissions import IsAuthenticated as ISA
            # non-admins can only update their own profile — enforced by get_queryset
            return [IsAuthenticated()]
        return [IsAuthenticated()]
