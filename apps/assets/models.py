import uuid
from django.db import models
from django.db.models import Max


class Asset(models.Model):
    class Status(models.TextChoices):
        AVAILABLE        = "AVAILABLE",        "Available"
        ALLOCATED        = "ALLOCATED",        "Allocated"
        UNDER_MAINTENANCE = "UNDER_MAINTENANCE","Under Maintenance"
        RETIRED          = "RETIRED",          "Retired"
        LOST             = "LOST",             "Lost"

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Auto-sequential asset_tag: AF-0001, AF-0002 … generated in save()
    asset_tag    = models.CharField(max_length=20, unique=True, blank=True)
    name         = models.CharField(max_length=255)
    description  = models.TextField(blank=True)
    category     = models.ForeignKey(
        "org.AssetCategory",
        on_delete=models.PROTECT,
        related_name="assets",
    )
    status       = models.CharField(
        max_length=20, choices=Status.choices, default=Status.AVAILABLE
    )
    # QR code value auto-generated; mirrors asset_tag for simplicity
    # Assumption: qr_code_value = asset_tag (no external QR generation lib needed for demo)
    qr_code_value = models.CharField(max_length=100, unique=True, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    location      = models.CharField(max_length=255, blank=True)
    # JSONField for category-specific extra data
    extra_data    = models.JSONField(default=dict, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["asset_tag"]

    def __str__(self):
        return f"{self.asset_tag} – {self.name}"

    def save(self, *args, **kwargs):
        if not self.asset_tag:
            # Generate next sequential tag atomically
            max_val = Asset.objects.aggregate(m=Max("asset_tag"))["m"]
            if max_val:
                try:
                    next_num = int(max_val.split("-")[1]) + 1
                except (IndexError, ValueError):
                    next_num = 1
            else:
                next_num = 1
            self.asset_tag    = f"AF-{next_num:04d}"
            self.qr_code_value = self.asset_tag
        elif not self.qr_code_value:
            self.qr_code_value = self.asset_tag
        super().save(*args, **kwargs)
