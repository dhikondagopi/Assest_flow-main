import uuid
from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    Lightweight activity feed. verb is a short machine-readable event code.
    target_id is a UUID string pointing to the relevant object (allocation, booking, etc.).
    Assumption: no polymorphic FK — just store target_id as string for simplicity.
    """
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    verb      = models.CharField(max_length=50)   # e.g. ASSET_ALLOCATED, TRANSFER_APPROVED
    message   = models.TextField()
    target_id = models.CharField(max_length=100, blank=True)  # UUID of related object
    is_read   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification({self.recipient.email}, {self.verb})"
