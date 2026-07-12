"""
Compatibility API views — serve the exact endpoint paths and JSON shapes the frontend expects.
Also provides CSV export endpoints and unread notification count.
"""
import csv
from io import StringIO

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.org.models import Department, AssetCategory, EmployeeProfile
from apps.assets.models import Asset
from apps.allocations.models import Allocation, TransferRequest
from apps.bookings.models import Booking
from apps.maintenance.models import MaintenanceRequest
from apps.notifications.models import Notification
from apps.notifications.utils import create_notification
from apps.users.permissions import IsAdmin, IsAdminOrAssetManager

from apps.compat.serializers import (
    CompatDepartmentSerializer,
    CompatCategorySerializer,
    CompatEmployeeSerializer,
    CompatAssetSerializer,
    CompatAllocationSerializer,
    CompatTransferSerializer,
    CompatBookingSerializer,
    CompatMaintenanceSerializer,
    CompatNotificationSerializer,
)

User = get_user_model()


# ── CSV helper ─────────────────────────────────────────────────────────────────

def csv_response(filename: str, rows: list[dict], fieldnames: list[str]) -> HttpResponse:
    buf = StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    resp = HttpResponse(buf.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


# ── Departments ────────────────────────────────────────────────────────────────

class CompatDepartmentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Department.objects.select_related("head__profile").prefetch_related("children")
        return Response(CompatDepartmentSerializer(qs, many=True).data)


# ── Categories ─────────────────────────────────────────────────────────────────

class CompatCategoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(CompatCategorySerializer(AssetCategory.objects.all(), many=True).data)


# ── Employees ──────────────────────────────────────────────────────────────────

class CompatEmployeeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = EmployeeProfile.objects.select_related("user", "department")
        return Response(CompatEmployeeSerializer(qs, many=True).data)


class CompatEmployeeRoleView(APIView):
    """PATCH /employees/<id>/role"""
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, pk):
        try:
            profile = EmployeeProfile.objects.select_related("user").get(pk=pk)
        except EmployeeProfile.DoesNotExist:
            return Response({"message": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)

        role = request.data.get("role")
        valid_roles = [r[0] for r in User.Role.choices]
        if role not in valid_roles:
            return Response({"message": f"Invalid role. Choose from: {valid_roles}"}, status=status.HTTP_400_BAD_REQUEST)

        if profile.user.pk == request.user.pk:
            return Response({"message": "You cannot change your own role."}, status=status.HTTP_400_BAD_REQUEST)

        profile.user.role = role
        profile.user.save(update_fields=["role"])
        return Response(CompatEmployeeSerializer(profile).data)


# ── Assets ─────────────────────────────────────────────────────────────────────

class CompatAssetListView(APIView):
    permission_classes = [IsAuthenticated]

    def _filtered_qs(self, request):
        qs = Asset.objects.select_related("category").prefetch_related("allocations__employee__department")
        q = request.query_params.get("q", "")
        status_f = request.query_params.get("status", "")
        category_f = request.query_params.get("category", "")
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(asset_tag__icontains=q) | Q(name__icontains=q) | Q(serial_number__icontains=q))
        if status_f:
            qs = qs.filter(status=status_f)
        if category_f:
            qs = qs.filter(category_id=category_f)
        return qs

    def get(self, request):
        return Response(CompatAssetSerializer(self._filtered_qs(request), many=True).data)


class CompatAssetDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            asset = Asset.objects.select_related("category").prefetch_related(
                "allocations__employee__department"
            ).get(pk=pk)
        except Asset.DoesNotExist:
            return Response({"code": "NOT_FOUND", "message": "Asset not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(CompatAssetSerializer(asset).data)


class CompatAssetExportView(APIView):
    """GET /assets/export/?q=&status=&category= → CSV"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Asset.objects.select_related("category").prefetch_related("allocations__employee__department")
        q = request.query_params.get("q", "")
        status_f = request.query_params.get("status", "")
        category_f = request.query_params.get("category", "")
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(asset_tag__icontains=q) | Q(name__icontains=q) | Q(serial_number__icontains=q))
        if status_f:
            qs = qs.filter(status=status_f)
        if category_f:
            qs = qs.filter(category_id=category_f)

        data = CompatAssetSerializer(qs, many=True).data
        rows = [
            {
                "Tag": r["tag"], "Name": r["name"], "Serial": r["serial"],
                "Status": r["status"], "Category": r.get("categoryId", ""),
                "Location": r["location"],
                "Value": r["value"],
                "Purchased": r["purchasedAt"],
            }
            for r in data
        ]
        return csv_response(
            "assets.csv", rows,
            ["Tag", "Name", "Serial", "Status", "Category", "Location", "Value", "Purchased"],
        )


# ── Allocations ────────────────────────────────────────────────────────────────

class CompatAllocationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Allocation.objects.select_related("asset", "employee__user").order_by("-allocated_at")
        return Response(CompatAllocationSerializer(qs, many=True).data)

    @transaction.atomic
    def post(self, request):
        asset_id    = request.data.get("assetId")
        employee_id = request.data.get("employeeId")
        due_at      = request.data.get("dueAt")

        if not asset_id or not employee_id:
            return Response({"code": "VALIDATION_ERROR", "message": "assetId and employeeId are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            asset = Asset.objects.get(pk=asset_id)
        except Asset.DoesNotExist:
            return Response({"code": "NOT_FOUND", "message": "Asset not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            employee = EmployeeProfile.objects.select_related("user").get(pk=employee_id)
        except EmployeeProfile.DoesNotExist:
            return Response({"code": "NOT_FOUND", "message": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)

        if asset.status == Asset.Status.ALLOCATED:
            active = Allocation.objects.filter(
                asset=asset, status=Allocation.Status.ACTIVE
            ).select_related("employee__user").first()
            if active:
                return Response(
                    {
                        "code": "ASSET_ALREADY_ALLOCATED",
                        "message": "Asset is currently held.",
                        "holderId": str(active.employee.id),
                        "holderName": active.employee.user.get_full_name(),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if asset.status not in (Asset.Status.AVAILABLE,):
            return Response(
                {"code": "ASSET_NOT_ALLOCATABLE", "message": f"Cannot allocate an asset in status {asset.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        due_date = None
        if due_at:
            try:
                from django.utils.dateparse import parse_date, parse_datetime
                parsed = parse_datetime(due_at) or parse_date(due_at)
                due_date = parsed.date() if hasattr(parsed, "date") else parsed
            except Exception:
                due_date = None

        alloc = Allocation.objects.create(
            asset=asset, employee=employee, allocated_by=request.user,
            status=Allocation.Status.ACTIVE, due_date=due_date,
        )
        asset.status = Asset.Status.ALLOCATED
        asset.save(update_fields=["status"])

        create_notification(
            recipient=employee.user, verb="ASSET_ALLOCATED",
            message=f"Asset {asset.asset_tag} ({asset.name}) has been allocated to you.",
            target_id=str(alloc.id),
        )
        return Response(CompatAllocationSerializer(alloc).data, status=status.HTTP_201_CREATED)


class CompatAllocationExportView(APIView):
    """GET /allocations/export/ → CSV of all allocations"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Allocation.objects.select_related(
            "asset", "employee__user"
        ).order_by("-allocated_at")
        data = CompatAllocationSerializer(qs, many=True).data
        rows = [
            {
                "ID": str(r["id"]),
                "Asset ID": str(r["assetId"]),
                "Employee ID": str(r["employeeId"]),
                "Allocated At": r["allocatedAt"] or "",
                "Returned At": r["returnedAt"] or "",
                "Due At": r["dueAt"] or "",
            }
            for r in data
        ]
        return csv_response(
            "allocations.csv", rows,
            ["ID", "Asset ID", "Employee ID", "Allocated At", "Returned At", "Due At"],
        )


# ── Transfers ──────────────────────────────────────────────────────────────────

class CompatTransferListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = TransferRequest.objects.select_related(
            "asset", "from_employee__user", "to_employee__user"
        ).order_by("-created_at")
        return Response(CompatTransferSerializer(qs, many=True).data)

    def post(self, request):
        asset_id  = request.data.get("assetId")
        to_emp_id = request.data.get("toEmployeeId")
        note      = request.data.get("note", "")

        if not asset_id or not to_emp_id:
            return Response({"code": "VALIDATION_ERROR", "message": "assetId and toEmployeeId are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            asset = Asset.objects.get(pk=asset_id)
        except Asset.DoesNotExist:
            return Response({"code": "NOT_FOUND", "message": "Asset not found"}, status=status.HTTP_404_NOT_FOUND)

        active = Allocation.objects.filter(
            asset=asset, status=Allocation.Status.ACTIVE
        ).select_related("employee__user").first()

        if not active:
            return Response(
                {"code": "INVALID_TRANSFER", "message": "Asset is not currently allocated"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            to_employee = EmployeeProfile.objects.get(pk=to_emp_id)
        except EmployeeProfile.DoesNotExist:
            return Response({"code": "NOT_FOUND", "message": "Target employee not found"}, status=status.HTTP_404_NOT_FOUND)

        transfer = TransferRequest.objects.create(
            asset=asset, from_employee=active.employee, to_employee=to_employee,
            requested_by=request.user, reason=note, status=TransferRequest.Status.PENDING,
        )
        return Response(CompatTransferSerializer(transfer).data, status=status.HTTP_201_CREATED)


class CompatTransferDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, pk):
        try:
            transfer = TransferRequest.objects.select_related(
                "asset", "from_employee__user", "to_employee__user"
            ).get(pk=pk)
        except TransferRequest.DoesNotExist:
            return Response({"code": "NOT_FOUND", "message": "Transfer not found"}, status=status.HTTP_404_NOT_FOUND)

        fe_status = request.data.get("status")

        if fe_status == "APPROVED":
            if transfer.status != TransferRequest.Status.PENDING:
                return Response({"message": f"Transfer is already {transfer.status}."}, status=status.HTTP_400_BAD_REQUEST)
            transfer.status = TransferRequest.Status.APPROVED
            transfer.approved_by = request.user
            transfer.save(update_fields=["status", "approved_by"])

        elif fe_status == "REALLOCATED":
            if transfer.status != TransferRequest.Status.APPROVED:
                return Response({"message": "Transfer must be APPROVED before completing reallocation."}, status=status.HTTP_400_BAD_REQUEST)
            old_alloc = Allocation.objects.filter(
                asset=transfer.asset, employee=transfer.from_employee,
                status=Allocation.Status.ACTIVE,
            ).first()
            if old_alloc:
                old_alloc.status = Allocation.Status.CLOSED
                old_alloc.returned_at = timezone.now()
                old_alloc.save(update_fields=["status", "returned_at"])

            Allocation.objects.create(
                asset=transfer.asset, employee=transfer.to_employee,
                allocated_by=request.user, status=Allocation.Status.ACTIVE,
                notes=f"Via transfer {transfer.id}",
            )
            transfer.status = TransferRequest.Status.APPROVED
            transfer.resolved_at = timezone.now()
            transfer.save(update_fields=["status", "resolved_at"])
            create_notification(
                recipient=transfer.to_employee.user, verb="ASSET_ALLOCATED",
                message=f"Asset {transfer.asset.asset_tag} has been transferred to you.",
                target_id=str(transfer.id),
            )

        elif fe_status == "REJECTED":
            transfer.status = TransferRequest.Status.REJECTED
            transfer.approved_by = request.user
            transfer.resolved_at = timezone.now()
            transfer.save(update_fields=["status", "approved_by", "resolved_at"])

        else:
            return Response({"message": f"Unknown status '{fe_status}'."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(CompatTransferSerializer(transfer).data)


# ── Bookings ───────────────────────────────────────────────────────────────────

class CompatBookingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Booking.objects.select_related("asset", "booked_by").order_by("-start_time")
        return Response(CompatBookingSerializer(qs, many=True).data)

    def post(self, request):
        asset_id = request.data.get("assetId")
        start_at = request.data.get("startAt")
        end_at   = request.data.get("endAt")
        purpose  = request.data.get("purpose", "")

        if not all([asset_id, start_at, end_at]):
            return Response({"code": "VALIDATION_ERROR", "message": "assetId, startAt, endAt are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            asset = Asset.objects.get(pk=asset_id)
        except Asset.DoesNotExist:
            return Response({"code": "NOT_FOUND", "message": "Asset not found"}, status=status.HTTP_404_NOT_FOUND)

        from django.utils.dateparse import parse_datetime
        start = parse_datetime(start_at)
        end   = parse_datetime(end_at)

        if not start or not end:
            return Response({"code": "INVALID_RANGE", "message": "Invalid datetime format."}, status=status.HTTP_400_BAD_REQUEST)
        if end <= start:
            return Response({"code": "INVALID_RANGE", "message": "End time must be after start time."}, status=status.HTTP_400_BAD_REQUEST)

        conflict = Booking.objects.filter(
            asset=asset,
            status__in=(Booking.Status.CONFIRMED, Booking.Status.PENDING),
            start_time__lt=end,
            end_time__gt=start,
        ).select_related("booked_by__profile").first()

        if conflict:
            holder_name = conflict.booked_by.get_full_name() if conflict.booked_by else "Unknown"
            return Response(
                {
                    "code": "BOOKING_OVERLAP",
                    "message": "Booking overlaps an existing reservation.",
                    "conflictStart":   conflict.start_time.isoformat(),
                    "conflictEnd":     conflict.end_time.isoformat(),
                    "conflictHolder":  holder_name,
                    "conflictPurpose": conflict.purpose,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking = Booking.objects.create(
            asset=asset, booked_by=request.user,
            start_time=start, end_time=end, purpose=purpose,
            status=Booking.Status.CONFIRMED,
        )
        create_notification(
            recipient=request.user, verb="BOOKING_CONFIRMED",
            message=f"Booking for {asset.asset_tag} ({asset.name}) from {start.strftime('%H:%M')} to {end.strftime('%H:%M')} confirmed.",
            target_id=str(booking.id),
        )
        return Response(CompatBookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class CompatBookingExportView(APIView):
    """GET /bookings/export/ → CSV"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Booking.objects.select_related("asset", "booked_by").order_by("-start_time")
        data = CompatBookingSerializer(qs, many=True).data
        rows = [
            {
                "ID": str(r["id"]),
                "Asset ID": str(r["assetId"]),
                "Employee ID": str(r["employeeId"] or ""),
                "Start": r["startAt"],
                "End": r["endAt"],
                "Purpose": r["purpose"],
            }
            for r in data
        ]
        return csv_response(
            "bookings.csv", rows,
            ["ID", "Asset ID", "Employee ID", "Start", "End", "Purpose"],
        )


# ── Maintenance ────────────────────────────────────────────────────────────────

class CompatMaintenanceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = MaintenanceRequest.objects.select_related(
            "asset", "requested_by", "assigned_to"
        ).order_by("-created_at")
        return Response(CompatMaintenanceSerializer(qs, many=True).data)

    def post(self, request):
        asset_id = request.data.get("assetId")
        issue    = request.data.get("issue", "")

        if not asset_id or not issue:
            return Response({"code": "VALIDATION_ERROR", "message": "assetId and issue are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            asset = Asset.objects.get(pk=asset_id)
        except Asset.DoesNotExist:
            return Response({"code": "NOT_FOUND", "message": "Asset not found"}, status=status.HTTP_404_NOT_FOUND)

        mr = MaintenanceRequest.objects.create(
            asset=asset, requested_by=request.user,
            description=issue, status=MaintenanceRequest.Status.PENDING,
        )
        return Response(CompatMaintenanceSerializer(mr).data, status=status.HTTP_201_CREATED)


class CompatMaintenanceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, pk):
        try:
            mr = MaintenanceRequest.objects.select_related("asset", "requested_by").get(pk=pk)
        except MaintenanceRequest.DoesNotExist:
            return Response({"code": "NOT_FOUND", "message": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)

        fe_status     = request.data.get("status")
        technician_id = request.data.get("technicianId")

        STATUS_MAP = {
            "APPROVED":    MaintenanceRequest.Status.APPROVED,
            "ASSIGNED":    MaintenanceRequest.Status.APPROVED,
            "IN_PROGRESS": MaintenanceRequest.Status.IN_PROGRESS,
            "RESOLVED":    MaintenanceRequest.Status.RESOLVED,
            "REJECTED":    MaintenanceRequest.Status.REJECTED,
        }
        if fe_status not in STATUS_MAP:
            return Response({"message": f"Unknown status '{fe_status}'."}, status=status.HTTP_400_BAD_REQUEST)

        mr.status = STATUS_MAP[fe_status]

        if technician_id:
            try:
                tech_profile = EmployeeProfile.objects.select_related("user").get(pk=technician_id)
                mr.assigned_to = tech_profile.user
            except EmployeeProfile.DoesNotExist:
                return Response({"message": "Technician not found."}, status=status.HTTP_400_BAD_REQUEST)

        if fe_status == "RESOLVED":
            mr.asset.status = Asset.Status.AVAILABLE
            mr.asset.save(update_fields=["status"])
        elif fe_status in ("APPROVED", "ASSIGNED"):
            mr.asset.status = Asset.Status.UNDER_MAINTENANCE
            mr.asset.save(update_fields=["status"])

        mr.save()

        if mr.requested_by:
            create_notification(
                recipient=mr.requested_by,
                verb=f"MAINTENANCE_{fe_status}",
                message=f"Your maintenance request for {mr.asset.asset_tag} has been updated to: {fe_status}.",
                target_id=str(mr.id),
            )
        return Response(CompatMaintenanceSerializer(mr).data)


class CompatMaintenanceExportView(APIView):
    """GET /maintenance/export/ → CSV"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = MaintenanceRequest.objects.select_related(
            "asset", "requested_by", "assigned_to"
        ).order_by("-created_at")
        data = CompatMaintenanceSerializer(qs, many=True).data
        rows = [
            {
                "ID": str(r["id"]),
                "Asset ID": str(r["assetId"]),
                "Issue": r["issue"],
                "Status": r["status"],
                "Raised By": str(r["raisedById"] or ""),
                "Technician": str(r["technicianId"] or ""),
                "Raised At": r["raisedAt"],
                "Resolved At": r["resolvedAt"] or "",
            }
            for r in data
        ]
        return csv_response(
            "maintenance.csv", rows,
            ["ID", "Asset ID", "Issue", "Status", "Raised By", "Technician", "Raised At", "Resolved At"],
        )


# ── Notifications ──────────────────────────────────────────────────────────────

class CompatNotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(recipient=request.user).order_by("-created_at")
        # Optional ?unread=true filter
        if request.query_params.get("unread") == "true":
            qs = qs.filter(is_read=False)
        return Response(CompatNotificationSerializer(qs, many=True).data)


class CompatNotificationReadView(APIView):
    """POST /notifications/<id>/read"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            n = Notification.objects.get(pk=pk, recipient=request.user)
        except Notification.DoesNotExist:
            return Response({"message": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        n.is_read = True
        n.save(update_fields=["is_read"])
        return Response({"ok": True})


class CompatNotificationReadAllView(APIView):
    """POST /notifications/read-all"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"ok": True})


class CompatUnreadCountView(APIView):
    """GET /notifications/unread-count/ → { unread_count: N }"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"unread_count": count})
