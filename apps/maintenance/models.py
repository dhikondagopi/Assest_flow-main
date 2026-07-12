import uuid
from django.db import models
from django.conf import settings


class MaintenanceRequest(models.Model):
    class Status(models.TextChoices):
        PENDING   = "PENDING",   "Pending"
        APPROVED  = "APPROVED",  "Approved"     # asset → UNDER_MAINTENANCE
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED  = "RESOLVED",  "Resolved"     # asset → AVAILABLE
        REJECTED  = "REJECTED",  "Rejected"

    class Priority(models.TextChoices):
        LOW    = "LOW",    "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH   = "HIGH",   "High"

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset        = models.ForeignKey(
        "assets.Asset", on_delete=models.PROTECT, related_name="maintenance_requests"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="maintenance_requests_raised",
    )
    assigned_to  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_requests_assigned",
    )
    status       = models.CharField(
        max_length=15, choices=Status.choices, default=Status.PENDING
    )
    priority     = models.CharField(
        max_length=6, choices=Priority.choices, default=Priority.MEDIUM
    )
    description  = models.TextField()
    resolution_notes = models.TextField(blank=True)
    scheduled_date   = models.DateField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Maintenance {self.asset.asset_tag} [{self.status}]"
