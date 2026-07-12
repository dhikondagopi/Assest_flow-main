import uuid
from django.db import models
from django.conf import settings


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING   = "PENDING",   "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Resource being booked — reuses the Asset model (bookable assets like meeting rooms, vehicles)
    asset       = models.ForeignKey(
        "assets.Asset", on_delete=models.PROTECT, related_name="bookings"
    )
    booked_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    start_time  = models.DateTimeField()
    end_time    = models.DateTimeField()
    purpose     = models.TextField(blank=True)
    status      = models.CharField(
        max_length=10, choices=Status.choices, default=Status.CONFIRMED
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_time"]

    def __str__(self):
        return f"Booking {self.asset.asset_tag} by {self.booked_by.get_full_name()} [{self.start_time}–{self.end_time}]"
