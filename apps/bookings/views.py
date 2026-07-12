from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdminOrAssetManagerOrDeptHead
from apps.bookings.models import Booking
from apps.bookings.serializers import BookingSerializer, BookingRescheduleSerializer


class BookingListCreateView(generics.ListCreateAPIView):
    """
    GET  — own bookings for employees; all for admin/manager/dept-head
    POST — any authenticated user (Dept Head, Employee, Admin, Manager)
    """
    serializer_class = BookingSerializer
    ordering_fields  = ["start_time", "created_at"]
    ordering         = ["-start_time"]
    search_fields    = ["asset__asset_tag", "asset__name", "purpose"]

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs   = Booking.objects.select_related("asset", "booked_by")
        if user.role in ("ADMIN", "ASSET_MANAGER"):
            return qs
        if user.role == "DEPARTMENT_HEAD":
            try:
                dept = user.profile.department
                dept_users = dept.members.values_list("user_id", flat=True)
                return qs.filter(booked_by__in=dept_users)
            except Exception:
                pass
        return qs.filter(booked_by=user)

    def perform_create(self, serializer):
        booking = serializer.save(booked_by=self.request.user)
        from apps.notifications.utils import create_notification
        create_notification(
            recipient=self.request.user,
            verb="BOOKING_CONFIRMED",
            message=(
                f"Your booking for {booking.asset.asset_tag} ({booking.asset.name}) "
                f"from {booking.start_time.strftime('%Y-%m-%d %H:%M')} to "
                f"{booking.end_time.strftime('%Y-%m-%d %H:%M')} is confirmed."
            ),
            target_id=str(booking.id),
        )


class BookingDetailView(generics.RetrieveAPIView):
    serializer_class   = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs   = Booking.objects.select_related("asset", "booked_by")
        if user.role in ("ADMIN", "ASSET_MANAGER"):
            return qs
        return qs.filter(booked_by=user)


class CancelBookingView(APIView):
    """POST /api/bookings/<id>/cancel/ — owner or Admin/Manager can cancel."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            booking = Booking.objects.select_related("asset", "booked_by").get(pk=pk)
        except Booking.DoesNotExist:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.role not in ("ADMIN", "ASSET_MANAGER") and booking.booked_by != user:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        if booking.status in (Booking.Status.CANCELLED, Booking.Status.COMPLETED):
            return Response(
                {"detail": f"Booking is already {booking.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=["status"])
        return Response({"message": "Booking cancelled.", "booking_id": str(booking.id)})


class RescheduleBookingView(APIView):
    """PATCH /api/bookings/<id>/reschedule/ — owner or Admin/Manager."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            booking = Booking.objects.select_related("asset", "booked_by").get(pk=pk)
        except Booking.DoesNotExist:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.role not in ("ADMIN", "ASSET_MANAGER") and booking.booked_by != user:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        if booking.status != Booking.Status.CONFIRMED:
            return Response(
                {"detail": f"Cannot reschedule a booking with status '{booking.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reschedule_serializer = BookingRescheduleSerializer(data=request.data)
        reschedule_serializer.is_valid(raise_exception=True)
        new_start = reschedule_serializer.validated_data["start_time"]
        new_end   = reschedule_serializer.validated_data["end_time"]

        # Re-run overlap check with new times using the main serializer's validate logic
        check_serializer = BookingSerializer(
            instance=booking,
            data={"start_time": new_start, "end_time": new_end, "asset": booking.asset.pk},
            partial=True,
        )
        check_serializer.is_valid(raise_exception=True)

        booking.start_time = new_start
        booking.end_time   = new_end
        booking.save(update_fields=["start_time", "end_time"])
        return Response(BookingSerializer(booking).data)


class CalendarView(APIView):
    """
    GET /api/bookings/calendar/?asset=<id>&start=<date>&end=<date>
    Returns bookings for a resource within a date range.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        asset_id   = request.query_params.get("asset")
        start_date = request.query_params.get("start")
        end_date   = request.query_params.get("end")

        if not all([asset_id, start_date, end_date]):
            return Response(
                {"detail": "Query params 'asset', 'start', and 'end' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = Booking.objects.filter(
            asset_id=asset_id,
            status__in=(Booking.Status.CONFIRMED, Booking.Status.PENDING),
            start_time__date__lte=end_date,
            end_time__date__gte=start_date,
        ).select_related("asset", "booked_by").order_by("start_time")

        return Response(BookingSerializer(qs, many=True).data)
