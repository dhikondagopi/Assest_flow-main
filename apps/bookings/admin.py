from django.contrib import admin
from apps.bookings.models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display  = ["asset", "booked_by", "start_time", "end_time", "status"]
    list_filter   = ["status"]
    search_fields = ["asset__asset_tag", "booked_by__email"]
    raw_id_fields = ["asset", "booked_by"]
    readonly_fields = ["created_at", "updated_at"]
