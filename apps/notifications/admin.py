from django.contrib import admin
from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ["recipient", "verb", "is_read", "created_at"]
    list_filter   = ["verb", "is_read"]
    search_fields = ["recipient__email", "message"]
    readonly_fields = ["created_at"]
