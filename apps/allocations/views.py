from django.db import transaction
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdmin, IsAdminOrAssetManager
from apps.allocations.models import Allocation, TransferRequest
from apps.allocations.serializers import AllocationSerializer, TransferRequestSerializer
from apps.assets.models import Asset


# ── Allocation ────────────────────────────────────────────────────────────────

class AllocationListCreateView(generics.ListCreateAPIView):
    """
    GET  — filtered per role
    POST — Asset Manager / Admin only
    """
    serializer_class = AllocationSerializer
    ordering_fields  = ["allocated_at", "due_date"]
    ordering         = ["-allocated_at"]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsAdminOrAssetManager()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs   = Allocation.objects.select_related(
            "asset", "employee__user", "allocated_by"
        )
        if user.role in ("ADMIN", "ASSET_MANAGER"):
            return qs
        if user.role == "DEPARTMENT_HEAD":
            try:
                dept = user.profile.department
            except Exception:
                return qs.none()
            return qs.filter(employee__department=dept)
        # Employee: own allocations only
        try:
            return qs.filter(employee__user=user)
        except Exception:
            return qs.none()

    @transaction.atomic
    def perform_create(self, serializer):
        asset = serializer.validated_data["asset"]
        alloc = serializer.save(allocated_by=self.request.user)
        # Update asset status
        asset.status = Asset.Status.ALLOCATED
        asset.save(update_fields=["status"])
        # Notify
        from apps.notifications.utils import create_notification
        create_notification(
            recipient=alloc.employee.user,
            verb="ASSET_ALLOCATED",
            message=f"Asset {asset.asset_tag} ({asset.name}) has been allocated to you.",
            target_id=str(alloc.id),
        )


class AllocationDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = AllocationSerializer
    permission_classes = [IsAuthenticated, IsAdminOrAssetManager]

    def get_queryset(self):
        return Allocation.objects.select_related("asset", "employee__user", "allocated_by")


class ReturnAllocationView(APIView):
    """
    POST /api/allocations/<id>/return/
    Marks allocation RETURNED, sets asset back to AVAILABLE.
    Employee can return own; Asset Manager / Admin can return any.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        try:
            alloc = Allocation.objects.select_related("asset", "employee__user").get(pk=pk)
        except Allocation.DoesNotExist:
            return Response({"detail": "Allocation not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        # Permission check
        if user.role not in ("ADMIN", "ASSET_MANAGER"):
            try:
                if alloc.employee.user != user:
                    return Response(
                        {"detail": "You can only return your own allocations."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except Exception:
                return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        if alloc.status != Allocation.Status.ACTIVE:
            return Response(
                {"detail": f"Cannot return: allocation is already {alloc.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        alloc.status      = Allocation.Status.RETURNED
        alloc.returned_at = timezone.now()
        alloc.save(update_fields=["status", "returned_at"])

        asset = alloc.asset
        asset.status = Asset.Status.AVAILABLE
        asset.save(update_fields=["status"])

        from apps.notifications.utils import create_notification
        create_notification(
            recipient=alloc.employee.user,
            verb="ASSET_RETURNED",
            message=f"Asset {asset.asset_tag} ({asset.name}) has been marked as returned.",
            target_id=str(alloc.id),
        )

        return Response({"message": "Asset returned successfully.", "allocation_id": str(alloc.id)})


class OverdueAllocationsView(generics.ListAPIView):
    """GET /api/allocations/overdue/ — active allocations past their due_date."""
    serializer_class   = AllocationSerializer
    permission_classes = [IsAuthenticated, IsAdminOrAssetManager]

    def get_queryset(self):
        return Allocation.objects.filter(
            status=Allocation.Status.ACTIVE,
            due_date__lt=timezone.now().date(),
        ).select_related("asset", "employee__user", "allocated_by")


# ── Transfer ──────────────────────────────────────────────────────────────────

class TransferRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = TransferRequestSerializer
    ordering_fields  = ["created_at"]
    ordering         = ["-created_at"]

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs   = TransferRequest.objects.select_related(
            "asset", "from_employee__user", "to_employee__user"
        )
        if user.role in ("ADMIN", "ASSET_MANAGER"):
            return qs
        try:
            return qs.filter(requested_by=user)
        except Exception:
            return qs.none()

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)


class TransferRequestDetailView(generics.RetrieveAPIView):
    serializer_class   = TransferRequestSerializer
    permission_classes = [IsAuthenticated]
    queryset = TransferRequest.objects.select_related(
        "asset", "from_employee__user", "to_employee__user"
    )


class ApproveTransferView(APIView):
    """
    POST /api/allocations/transfers/<id>/approve/
    Asset Manager / Admin only. Atomic: close old allocation, create new one, log.
    """
    permission_classes = [IsAuthenticated, IsAdminOrAssetManager]

    @transaction.atomic
    def post(self, request, pk):
        try:
            transfer = TransferRequest.objects.select_related(
                "asset", "from_employee__user", "to_employee__user"
            ).get(pk=pk)
        except TransferRequest.DoesNotExist:
            return Response({"detail": "Transfer request not found."}, status=status.HTTP_404_NOT_FOUND)

        if transfer.status != TransferRequest.Status.PENDING:
            return Response(
                {"detail": f"Transfer is already {transfer.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Close existing active allocation
        old_alloc = Allocation.objects.filter(
            asset=transfer.asset,
            employee=transfer.from_employee,
            status=Allocation.Status.ACTIVE,
        ).first()

        if old_alloc:
            old_alloc.status      = Allocation.Status.CLOSED
            old_alloc.returned_at = timezone.now()
            old_alloc.save(update_fields=["status", "returned_at"])

        # Create new allocation for target employee
        new_alloc = Allocation.objects.create(
            asset        = transfer.asset,
            employee     = transfer.to_employee,
            allocated_by = request.user,
            status       = Allocation.Status.ACTIVE,
            notes        = f"Via transfer request {transfer.id}",
        )

        # Mark transfer approved
        transfer.status      = TransferRequest.Status.APPROVED
        transfer.approved_by = request.user
        transfer.resolved_at = timezone.now()
        transfer.save(update_fields=["status", "approved_by", "resolved_at"])

        # Notify both parties
        from apps.notifications.utils import create_notification
        create_notification(
            recipient=transfer.from_employee.user,
            verb="TRANSFER_APPROVED",
            message=(
                f"Transfer of {transfer.asset.asset_tag} to "
                f"{transfer.to_employee.user.get_full_name()} has been approved."
            ),
            target_id=str(transfer.id),
        )
        create_notification(
            recipient=transfer.to_employee.user,
            verb="ASSET_ALLOCATED",
            message=(
                f"Asset {transfer.asset.asset_tag} ({transfer.asset.name}) "
                "has been transferred to you."
            ),
            target_id=str(new_alloc.id),
        )

        return Response(
            {
                "message": "Transfer approved.",
                "new_allocation_id": str(new_alloc.id),
                "transfer_id": str(transfer.id),
            }
        )


class RejectTransferView(APIView):
    """POST /api/allocations/transfers/<id>/reject/ — Asset Manager / Admin."""
    permission_classes = [IsAuthenticated, IsAdminOrAssetManager]

    def post(self, request, pk):
        try:
            transfer = TransferRequest.objects.get(pk=pk)
        except TransferRequest.DoesNotExist:
            return Response({"detail": "Transfer request not found."}, status=status.HTTP_404_NOT_FOUND)

        if transfer.status != TransferRequest.Status.PENDING:
            return Response(
                {"detail": f"Transfer is already {transfer.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        transfer.status      = TransferRequest.Status.REJECTED
        transfer.approved_by = request.user
        transfer.resolved_at = timezone.now()
        transfer.save(update_fields=["status", "approved_by", "resolved_at"])

        return Response({"message": "Transfer rejected.", "transfer_id": str(transfer.id)})
