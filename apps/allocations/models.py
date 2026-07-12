import uuid
from django.db import models
from django.conf import settings


class Allocation(models.Model):
    class Status(models.TextChoices):
        ACTIVE    = "ACTIVE",    "Active"
        RETURNED  = "RETURNED",  "Returned"
        CLOSED    = "CLOSED",    "Closed"   # closed by a transfer approval

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset        = models.ForeignKey(
        "assets.Asset", on_delete=models.PROTECT, related_name="allocations"
    )
    employee     = models.ForeignKey(
        "org.EmployeeProfile", on_delete=models.PROTECT, related_name="allocations"
    )
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="allocations_made",
    )
    status       = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    allocated_at = models.DateTimeField(auto_now_add=True)
    # due_date: assumption — optional; overdue if due_date < now and status=ACTIVE
    due_date     = models.DateField(null=True, blank=True)
    returned_at  = models.DateTimeField(null=True, blank=True)
    notes        = models.TextField(blank=True)

    class Meta:
        ordering = ["-allocated_at"]

    def __str__(self):
        return f"{self.asset.asset_tag} → {self.employee.user.get_full_name()}"


class TransferRequest(models.Model):
    class Status(models.TextChoices):
        PENDING   = "PENDING",   "Pending"
        APPROVED  = "APPROVED",  "Approved"
        REJECTED  = "REJECTED",  "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset           = models.ForeignKey(
        "assets.Asset", on_delete=models.PROTECT, related_name="transfer_requests"
    )
    from_employee   = models.ForeignKey(
        "org.EmployeeProfile",
        on_delete=models.PROTECT,
        related_name="transfers_out",
    )
    to_employee     = models.ForeignKey(
        "org.EmployeeProfile",
        on_delete=models.PROTECT,
        related_name="transfers_in",
    )
    requested_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="transfer_requests_made",
    )
    approved_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transfer_requests_approved",
    )
    status          = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    reason          = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    resolved_at     = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Transfer {self.asset.asset_tag}: {self.from_employee} → {self.to_employee}"
