"""
Compatibility serializers — output field names that match the frontend TypeScript types exactly.

Frontend type → Backend model mapping:
  Employee.id             → EmployeeProfile.id  (UUID)
  Employee.fullName       → User.get_full_name()
  Employee.email          → User.email
  Employee.role           → User.role
  Employee.departmentId   → EmployeeProfile.department_id
  Employee.title          → EmployeeProfile.phone (repurposed as title — see note below)

  Asset.id                → Asset.id
  Asset.tag               → Asset.asset_tag
  Asset.serial            → Asset.serial_number
  Asset.name              → Asset.name
  Asset.categoryId        → Asset.category_id
  Asset.status            → Asset.status  (RESERVED not in backend → treat as AVAILABLE)
  Asset.departmentId      → from active allocation's employee's department (best-effort)
  Asset.location          → Asset.location
  Asset.assignedToId      → from active allocation's employee profile id
  Asset.purchasedAt       → Asset.purchase_date (as ISO string)
  Asset.value             → Asset.purchase_cost

  Allocation.id           → Allocation.id
  Allocation.assetId      → Allocation.asset_id
  Allocation.employeeId   → Allocation.employee_id  (EmployeeProfile UUID)
  Allocation.allocatedAt  → Allocation.allocated_at
  Allocation.returnedAt   → Allocation.returned_at
  Allocation.dueAt        → Allocation.due_date

  Transfer.id             → TransferRequest.id
  Transfer.assetId        → TransferRequest.asset_id
  Transfer.fromEmployeeId → TransferRequest.from_employee_id
  Transfer.toEmployeeId   → TransferRequest.to_employee_id
  Transfer.status         REQUESTED→PENDING, APPROVED→APPROVED, REALLOCATED→APPROVED(completed), REJECTED→REJECTED
  Transfer.requestedAt    → TransferRequest.created_at
  Transfer.note           → TransferRequest.reason

  Booking.id              → Booking.id
  Booking.assetId         → Booking.asset_id
  Booking.employeeId      → EmployeeProfile.id of booked_by user
  Booking.startAt         → Booking.start_time
  Booking.endAt           → Booking.end_time
  Booking.purpose         → Booking.purpose

  MaintenanceTicket.id            → MaintenanceRequest.id
  MaintenanceTicket.assetId       → MaintenanceRequest.asset_id
  MaintenanceTicket.raisedById    → EmployeeProfile.id of requested_by user
  MaintenanceTicket.technicianId  → EmployeeProfile.id of assigned_to user
  MaintenanceTicket.status        → MaintenanceRequest.status (ASSIGNED mapped to IN_PROGRESS)
  MaintenanceTicket.issue         → MaintenanceRequest.description
  MaintenanceTicket.raisedAt      → MaintenanceRequest.created_at
  MaintenanceTicket.resolvedAt    → MaintenanceRequest.updated_at (only if RESOLVED)

  Notification.id         → Notification.id
  Notification.title      → derived from Notification.verb
  Notification.body       → Notification.message
  Notification.createdAt  → Notification.created_at
  Notification.read       → Notification.is_read
  Notification.kind       → derived from Notification.verb

Note on Employee.title: The EmployeeProfile model has a `phone` field.
We repurpose it to store job title in the seed and compatibility layer.
A proper fix would be adding a `title` field to EmployeeProfile.
"""
from rest_framework import serializers
from apps.org.models import Department, AssetCategory, EmployeeProfile
from apps.assets.models import Asset
from apps.allocations.models import Allocation, TransferRequest
from apps.bookings.models import Booking
from apps.maintenance.models import MaintenanceRequest
from apps.notifications.models import Notification


# ── Helpers ────────────────────────────────────────────────────────────────────

def _profile_id_for_user(user):
    """Return the EmployeeProfile UUID for a User, or None."""
    if user is None:
        return None
    try:
        return str(user.profile.id)
    except Exception:
        return None


VERB_TO_KIND = {
    "ASSET_ALLOCATED":    "success",
    "ASSET_RETURNED":     "info",
    "TRANSFER_APPROVED":  "success",
    "TRANSFER_PENDING":   "info",
    "BOOKING_CONFIRMED":  "success",
    "MAINTENANCE_APPROVED": "success",
    "MAINTENANCE_RESOLVED": "success",
    "MAINTENANCE_REJECTED": "warning",
}
VERB_TO_TITLE = {
    "ASSET_ALLOCATED":    "Asset allocated",
    "ASSET_RETURNED":     "Asset returned",
    "TRANSFER_APPROVED":  "Transfer approved",
    "TRANSFER_PENDING":   "Transfer request",
    "BOOKING_CONFIRMED":  "Booking confirmed",
    "MAINTENANCE_APPROVED": "Maintenance approved",
    "MAINTENANCE_RESOLVED": "Maintenance resolved",
    "MAINTENANCE_REJECTED": "Maintenance rejected",
}

TRANSFER_STATUS_MAP = {
    "PENDING":  "REQUESTED",
    "APPROVED": "APPROVED",
    "REJECTED": "REJECTED",
    "CANCELLED":"REJECTED",
}


# ── Department ─────────────────────────────────────────────────────────────────

class CompatDepartmentSerializer(serializers.ModelSerializer):
    parentId = serializers.SerializerMethodField()
    headId   = serializers.SerializerMethodField()

    class Meta:
        model  = Department
        fields = ["id", "name", "parentId", "headId"]

    def get_parentId(self, obj):
        return str(obj.parent_id) if obj.parent_id else None

    def get_headId(self, obj):
        return _profile_id_for_user(obj.head) if obj.head else None


# ── AssetCategory ──────────────────────────────────────────────────────────────

class CompatCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = AssetCategory
        fields = ["id", "name", "description"]


# ── Employee ───────────────────────────────────────────────────────────────────

class CompatEmployeeSerializer(serializers.ModelSerializer):
    fullName     = serializers.SerializerMethodField()
    email        = serializers.EmailField(source="user.email")
    role         = serializers.CharField(source="user.role")
    departmentId = serializers.SerializerMethodField()
    title        = serializers.SerializerMethodField()

    class Meta:
        model  = EmployeeProfile
        fields = ["id", "fullName", "email", "role", "departmentId", "title"]

    def get_fullName(self, obj):
        return obj.user.get_full_name()

    def get_departmentId(self, obj):
        return str(obj.department_id) if obj.department_id else None

    def get_title(self, obj):
        return obj.title or obj.phone or obj.user.get_full_name()


# ── Asset ──────────────────────────────────────────────────────────────────────

class CompatAssetSerializer(serializers.ModelSerializer):
    tag          = serializers.CharField(source="asset_tag")
    serial       = serializers.CharField(source="serial_number")
    categoryId   = serializers.SerializerMethodField()
    departmentId = serializers.SerializerMethodField()
    assignedToId = serializers.SerializerMethodField()
    purchasedAt  = serializers.SerializerMethodField()
    value        = serializers.SerializerMethodField()

    class Meta:
        model  = Asset
        fields = [
            "id", "tag", "serial", "name",
            "categoryId", "status", "departmentId",
            "location", "assignedToId",
            "purchasedAt", "value",
        ]

    def get_categoryId(self, obj):
        return str(obj.category_id) if obj.category_id else None

    def get_departmentId(self, obj):
        # Get department from the active allocation's employee
        active = obj.allocations.filter(status=Allocation.Status.ACTIVE).select_related(
            "employee__department"
        ).first()
        if active and active.employee.department_id:
            return str(active.employee.department_id)
        return None

    def get_assignedToId(self, obj):
        # Return the EmployeeProfile UUID of the currently allocated employee
        active = obj.allocations.filter(status=Allocation.Status.ACTIVE).first()
        if active:
            return str(active.employee_id)
        return None

    def get_purchasedAt(self, obj):
        if obj.purchase_date:
            return obj.purchase_date.isoformat()
        return obj.created_at.isoformat()

    def get_value(self, obj):
        return float(obj.purchase_cost) if obj.purchase_cost else 0


# ── Allocation ─────────────────────────────────────────────────────────────────

class CompatAllocationSerializer(serializers.ModelSerializer):
    assetId    = serializers.UUIDField(source="asset_id")
    employeeId = serializers.UUIDField(source="employee_id")
    allocatedAt = serializers.DateTimeField(source="allocated_at")
    returnedAt  = serializers.DateTimeField(source="returned_at")
    dueAt       = serializers.SerializerMethodField()

    class Meta:
        model  = Allocation
        fields = ["id", "assetId", "employeeId", "allocatedAt", "returnedAt", "dueAt"]

    def get_dueAt(self, obj):
        if obj.due_date:
            # Return as ISO datetime string (frontend uses new Date())
            from datetime import datetime, timezone
            return datetime.combine(obj.due_date, datetime.min.time()).replace(tzinfo=timezone.utc).isoformat()
        return None


# ── Transfer ───────────────────────────────────────────────────────────────────

class CompatTransferSerializer(serializers.ModelSerializer):
    assetId         = serializers.UUIDField(source="asset_id")
    fromEmployeeId  = serializers.UUIDField(source="from_employee_id")
    toEmployeeId    = serializers.UUIDField(source="to_employee_id")
    status          = serializers.SerializerMethodField()
    requestedAt     = serializers.DateTimeField(source="created_at")
    note            = serializers.CharField(source="reason")

    class Meta:
        model  = TransferRequest
        fields = [
            "id", "assetId", "fromEmployeeId", "toEmployeeId",
            "status", "requestedAt", "note",
        ]

    def get_status(self, obj):
        return TRANSFER_STATUS_MAP.get(obj.status, "REQUESTED")


# ── Booking ────────────────────────────────────────────────────────────────────

class CompatBookingSerializer(serializers.ModelSerializer):
    assetId    = serializers.UUIDField(source="asset_id")
    employeeId = serializers.SerializerMethodField()
    startAt    = serializers.DateTimeField(source="start_time")
    endAt      = serializers.DateTimeField(source="end_time")

    class Meta:
        model  = Booking
        fields = ["id", "assetId", "employeeId", "startAt", "endAt", "purpose"]

    def get_employeeId(self, obj):
        return _profile_id_for_user(obj.booked_by)


# ── Maintenance ────────────────────────────────────────────────────────────────

class CompatMaintenanceSerializer(serializers.ModelSerializer):
    assetId      = serializers.UUIDField(source="asset_id")
    raisedById   = serializers.SerializerMethodField()
    technicianId = serializers.SerializerMethodField()
    status       = serializers.SerializerMethodField()
    issue        = serializers.CharField(source="description")
    raisedAt     = serializers.DateTimeField(source="created_at")
    resolvedAt   = serializers.SerializerMethodField()

    class Meta:
        model  = MaintenanceRequest
        fields = [
            "id", "assetId", "raisedById", "technicianId",
            "status", "issue", "raisedAt", "resolvedAt",
        ]

    def get_raisedById(self, obj):
        return _profile_id_for_user(obj.requested_by)

    def get_technicianId(self, obj):
        return _profile_id_for_user(obj.assigned_to)

    def get_status(self, obj):
        # Frontend status set: PENDING, APPROVED, ASSIGNED, IN_PROGRESS, RESOLVED, REJECTED
        # Backend doesn't have ASSIGNED — map IN_PROGRESS → ASSIGNED so kanban shows correctly
        # Assumption: if assigned_to is set and status=APPROVED, treat as ASSIGNED in frontend
        if obj.status == MaintenanceRequest.Status.APPROVED and obj.assigned_to:
            return "ASSIGNED"
        return obj.status  # PENDING, APPROVED, IN_PROGRESS, RESOLVED, REJECTED all pass through

    def get_resolvedAt(self, obj):
        if obj.status == MaintenanceRequest.Status.RESOLVED:
            return obj.updated_at.isoformat()
        return None


# ── Notification ───────────────────────────────────────────────────────────────

class CompatNotificationSerializer(serializers.ModelSerializer):
    title     = serializers.SerializerMethodField()
    body      = serializers.CharField(source="message")
    createdAt = serializers.DateTimeField(source="created_at")
    read      = serializers.BooleanField(source="is_read")
    kind      = serializers.SerializerMethodField()

    class Meta:
        model  = Notification
        fields = ["id", "title", "body", "createdAt", "read", "kind"]

    def get_title(self, obj):
        return VERB_TO_TITLE.get(obj.verb, obj.verb.replace("_", " ").title())

    def get_kind(self, obj):
        return VERB_TO_KIND.get(obj.verb, "info")
