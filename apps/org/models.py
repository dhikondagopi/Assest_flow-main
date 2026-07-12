import uuid
from django.db import models
from django.conf import settings


class Department(models.Model):
    """Self-referential hierarchy; top-level departments have parent=None."""
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=255, unique=True)
    code        = models.CharField(max_length=20, unique=True)
    parent      = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    head        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
    )
    description = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class AssetCategory(models.Model):
    """
    extra_fields: JSONField schema hints for assets in this category.
    Assumption: stored as a list of dicts {name, type, required}.
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name         = models.CharField(max_length=255, unique=True)
    description  = models.TextField(blank=True)
    extra_fields = models.JSONField(
        default=list,
        blank=True,
        help_text='List of extra field definitions e.g. [{"name":"serial_no","type":"string","required":true}]',
    )
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Asset Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class EmployeeProfile(models.Model):
    """
    Extended profile attached 1-to-1 to User.
    Stores department assignment and employee-number.
    """
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user           = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    department     = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )
    employee_number = models.CharField(max_length=30, unique=True, blank=True)
    phone          = models.CharField(max_length=100, blank=True)  # also used as job title
    title          = models.CharField(max_length=150, blank=True)  # job title for frontend compat
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__first_name"]

    def __str__(self):
        return f"Profile({self.user.email})"
