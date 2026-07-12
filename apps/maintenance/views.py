from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdminOrAssetManager
from apps.assets.models import Asset
from apps.maintenance.models import MaintenanceRequest
from apps.maintenance.serializers import (
    MaintenanceRequestSerializer,
    MaintenanceStatusUpdateSerializer,
)

User = get_user_model()


class MaintenanceRequestListCreateView(generics.ListCreateAPIView):
    """
    GET  — Admin/Manager see all; Employee sees own requests
    POST — any authenticated user can raise a request
    """
    serializer_class = MaintenanceRequestSerializer
    ordering_fields  = ["created_at", "priority", "status"]
    ordering         = ["-created_at"]
    search_fields    = ["asset__asset_tag", "asset__name", "description"]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs   = MaintenanceRequest.objects.select_related(
            "asset", "requested_by", "assigned_to"
        )
        if user.role in ("ADMIN", "ASSET_MANAGER"):
            return qs
        return qs.filter(requested_by=user)

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)


class MaintenanceRequestDetailView(generics.RetrieveUpdateAPIView):
    serializer_class   = MaintenanceRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs   = MaintenanceRequest.objects.select_related("asset", "requested_by", "assigned_to")
        if user.role in ("ADMIN", "ASSET_MANAGER"):
            return qs
        return qs.filter(requested_by=user)

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH"):
            return [IsAuthenticated(), IsAdminOrAssetManager()]
        return [IsAuthenticated()]


class _BaseStatusTransitionView(APIView):
    """
    Shared base for status-transition endpoints.
    Subclasses define: target_status, allowed_from, asset_status_side_effect (optional).
    """
    permission_classes = [IsAuthenticated, IsAdminOrAssetManager]
    target_status      = None          # set in subclass
    allowed_from       = []            # set in subclass
    asset_side_effect  = None          # optional Asset.Status value

    @transaction.atomic
    def post(self, request, pk):
        try:
            mr = MaintenanceRequest.objects.select_related("asset", "requested_by").get(pk=pk)
        except MaintenanceRequest.DoesNotExist:
            return Response({"detail": "Maintenance request not found."}, status=status.HTTP_404_NOT_FOUND)

        if mr.status not in self.allowed_from:
            return Response(
                {"detail": f"Cannot transition to {self.target_status} from {mr.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = MaintenanceStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        mr.status = self.target_status

        if "resolution_notes" in data:
            mr.resolution_notes = data["resolution_notes"]
        if "scheduled_date" in data:
            mr.scheduled_date = data["scheduled_date"]
        if "assigned_to" in data and data["assigned_to"]:
            try:
                mr.assigned_to = User.objects.get(pk=data["assigned_to"])
            except User.DoesNotExist:
                return Response(
                    {"detail": "assigned_to user not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        mr.save()

        # Side-effect: change asset status
        if self.asset_side_effect:
            asset = mr.asset
            asset.status = self.asset_side_effect
            asset.save(update_fields=["status"])

        # Notify requester
        from apps.notifications.utils import create_notification
        create_notification(
            recipient=mr.requested_by,
            verb=f"MAINTENANCE_{self.target_status}",
            message=(
                f"Your maintenance request for {mr.asset.asset_tag} ({mr.asset.name}) "
                f"has been updated to: {self.target_status}."
            ),
            target_id=str(mr.id),
        )

        return Response(
            {
                "message": f"Maintenance request updated to {self.target_status}.",
                "id": str(mr.id),
                "status": mr.status,
            }
        )


class ApproveMaintenanceView(_BaseStatusTransitionView):
    """
    POST /api/maintenance/<id>/approve/
    PENDING → APPROVED; asset → UNDER_MAINTENANCE
    """
    target_status     = MaintenanceRequest.Status.APPROVED
    allowed_from      = [MaintenanceRequest.Status.PENDING]
    asset_side_effect = Asset.Status.UNDER_MAINTENANCE


class StartMaintenanceView(_BaseStatusTransitionView):
    """
    POST /api/maintenance/<id>/start/
    APPROVED → IN_PROGRESS
    """
    target_status = MaintenanceRequest.Status.IN_PROGRESS
    allowed_from  = [MaintenanceRequest.Status.APPROVED]


class ResolveMaintenanceView(_BaseStatusTransitionView):
    """
    POST /api/maintenance/<id>/resolve/
    IN_PROGRESS or APPROVED → RESOLVED; asset → AVAILABLE
    """
    target_status     = MaintenanceRequest.Status.RESOLVED
    allowed_from      = [
        MaintenanceRequest.Status.IN_PROGRESS,
        MaintenanceRequest.Status.APPROVED,
    ]
    asset_side_effect = Asset.Status.AVAILABLE


class RejectMaintenanceView(_BaseStatusTransitionView):
    """
    POST /api/maintenance/<id>/reject/
    PENDING → REJECTED; no asset side-effect
    """
    target_status = MaintenanceRequest.Status.REJECTED
    allowed_from  = [MaintenanceRequest.Status.PENDING]
