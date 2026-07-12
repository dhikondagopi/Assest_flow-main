from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdminOrAssetManager
from apps.assets.models import Asset
from apps.allocations.models import Allocation, TransferRequest
from apps.bookings.models import Booking
from apps.maintenance.models import MaintenanceRequest
from apps.allocations.serializers import AllocationSerializer


class DashboardView(APIView):
    """
    GET /api/dashboard/
    Single aggregate endpoint — Admin and Asset Manager only.
    Returns counts + overdue allocation list.
    """
    permission_classes = [IsAuthenticated, IsAdminOrAssetManager]

    def get(self, request):
        today = timezone.now().date()

        # Asset counts
        total_assets     = Asset.objects.count()
        available_assets = Asset.objects.filter(status=Asset.Status.AVAILABLE).count()
        allocated_assets = Asset.objects.filter(status=Asset.Status.ALLOCATED).count()
        under_maint      = Asset.objects.filter(status=Asset.Status.UNDER_MAINTENANCE).count()
        lost_assets      = Asset.objects.filter(status=Asset.Status.LOST).count()
        retired_assets   = Asset.objects.filter(status=Asset.Status.RETIRED).count()

        # Allocation counts
        active_allocations   = Allocation.objects.filter(status=Allocation.Status.ACTIVE).count()
        overdue_qs           = Allocation.objects.filter(
            status=Allocation.Status.ACTIVE,
            due_date__lt=today,
        ).select_related("asset", "employee__user", "allocated_by")
        overdue_count        = overdue_qs.count()

        # Transfer counts
        pending_transfers    = TransferRequest.objects.filter(
            status=TransferRequest.Status.PENDING
        ).count()

        # Booking counts
        upcoming_bookings    = Booking.objects.filter(
            status=Booking.Status.CONFIRMED,
            start_time__gte=timezone.now(),
        ).count()

        # Maintenance counts
        pending_maintenance  = MaintenanceRequest.objects.filter(
            status=MaintenanceRequest.Status.PENDING
        ).count()
        active_maintenance   = MaintenanceRequest.objects.filter(
            status__in=(
                MaintenanceRequest.Status.APPROVED,
                MaintenanceRequest.Status.IN_PROGRESS,
            )
        ).count()

        overdue_allocations = AllocationSerializer(overdue_qs[:10], many=True).data

        return Response(
            {
                "assets": {
                    "total":            total_assets,
                    "available":        available_assets,
                    "allocated":        allocated_assets,
                    "under_maintenance": under_maint,
                    "lost":             lost_assets,
                    "retired":          retired_assets,
                },
                "allocations": {
                    "active":           active_allocations,
                    "overdue":          overdue_count,
                },
                "transfers": {
                    "pending":          pending_transfers,
                },
                "bookings": {
                    "upcoming":         upcoming_bookings,
                },
                "maintenance": {
                    "pending":          pending_maintenance,
                    "active":           active_maintenance,
                },
                "overdue_allocations":  overdue_allocations,
            }
        )
