from django.contrib import admin
from apps.assets.models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display  = ["asset_tag", "name", "category", "status", "location", "purchase_cost"]
    list_filter   = ["status", "category"]
    search_fields = ["asset_tag", "name", "serial_number"]
    readonly_fields = ["asset_tag", "qr_code_value", "created_at", "updated_at"]
    ordering      = ["asset_tag"]
