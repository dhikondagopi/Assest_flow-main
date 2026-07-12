from django.contrib import admin
from apps.maintenance.models import MaintenanceRequest


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display  = ["asset", "status", "priority", "requested_by", "assigned_to", "created_at"]
    list_filter   = ["status", "priority"]
    search_fields = ["asset__asset_tag", "description"]
    raw_id_fields = ["asset", "requested_by", "assigned_to"]
    readonly_fields = ["created_at", "updated_at"]
