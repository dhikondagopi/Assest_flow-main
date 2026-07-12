from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdmin, IsAdminOrAssetManager
from apps.assets.models import Asset
from apps.assets.serializers import AssetSerializer, AssetListSerializer


class AssetListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/assets/         — all authenticated users (list)
    POST /api/assets/         — Asset Manager / Admin only
    Supports ?search=, ?status=, ?category=, ?location=
    """
    search_fields  = ["asset_tag", "name", "serial_number", "location"]
    ordering_fields = ["asset_tag", "name", "status", "created_at"]
    ordering        = ["asset_tag"]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAdminOrAssetManager()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return AssetListSerializer
        return AssetSerializer

    def get_queryset(self):
        qs = Asset.objects.select_related("category")
        status_filter   = self.request.query_params.get("status")
        category_filter = self.request.query_params.get("category")
        location_filter = self.request.query_params.get("location")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if category_filter:
            qs = qs.filter(category__id=category_filter)
        if location_filter:
            qs = qs.filter(location__icontains=location_filter)
        return qs


class AssetDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/PATCH /api/assets/<id>/ — Asset Manager/Admin writes; all read
    DELETE — Admin only
    """
    queryset         = Asset.objects.select_related("category")
    serializer_class = AssetSerializer

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAuthenticated(), IsAdmin()]
        if self.request.method in ("PUT", "PATCH"):
            return [IsAuthenticated(), IsAdminOrAssetManager()]
        return [IsAuthenticated()]


class AssetHistoryView(APIView):
    """
    GET /api/assets/<id>/history/
    Returns combined allocation + maintenance history sorted by date desc.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            asset = Asset.objects.get(pk=pk)
        except Asset.DoesNotExist:
            return Response({"detail": "Asset not found."}, status=status.HTTP_404_NOT_FOUND)

        from apps.allocations.models import Allocation
        from apps.maintenance.models import MaintenanceRequest
        from apps.allocations.serializers import AllocationSerializer
        from apps.maintenance.serializers import MaintenanceRequestSerializer

        allocations  = Allocation.objects.filter(asset=asset).select_related("employee__user")
        maintenance  = MaintenanceRequest.objects.filter(asset=asset).select_related("requested_by")

        alloc_data   = AllocationSerializer(allocations, many=True).data
        maint_data   = MaintenanceRequestSerializer(maintenance, many=True).data

        # Tag each entry with its type for frontend
        for entry in alloc_data:
            entry["history_type"] = "allocation"
        for entry in maint_data:
            entry["history_type"] = "maintenance"

        combined = list(alloc_data) + list(maint_data)
        # Sort by allocated_at / created_at descending
        combined.sort(
            key=lambda x: x.get("allocated_at") or x.get("created_at") or "",
            reverse=True,
        )
        return Response(combined)
