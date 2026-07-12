from django.contrib import admin
from apps.allocations.models import Allocation, TransferRequest


@admin.register(Allocation)
class AllocationAdmin(admin.ModelAdmin):
    list_display   = ["asset", "employee", "status", "allocated_at", "due_date", "returned_at"]
    list_filter    = ["status"]
    search_fields  = ["asset__asset_tag", "employee__user__email"]
    raw_id_fields  = ["asset", "employee", "allocated_by"]
    readonly_fields = ["allocated_at"]


@admin.register(TransferRequest)
class TransferRequestAdmin(admin.ModelAdmin):
    list_display  = ["asset", "from_employee", "to_employee", "status", "created_at"]
    list_filter   = ["status"]
    search_fields = ["asset__asset_tag"]
    raw_id_fields = ["asset", "from_employee", "to_employee", "requested_by", "approved_by"]
    readonly_fields = ["created_at", "resolved_at"]
