from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.users.models import User, PasswordResetToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ["email", "first_name", "last_name", "role", "is_active", "created_at"]
    list_filter   = ["role", "is_active", "is_staff"]
    search_fields = ["email", "first_name", "last_name"]
    ordering      = ["email"]
    fieldsets = (
        (None,               {"fields": ("email", "password")}),
        ("Personal info",    {"fields": ("first_name", "last_name")}),
        ("Role & status",    {"fields": ("role", "is_active", "is_staff", "is_superuser")}),
        ("Permissions",      {"fields": ("groups", "user_permissions")}),
        ("Important dates",  {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields":  ("email", "first_name", "last_name", "password1", "password2", "role"),
        }),
    )


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display  = ["user", "token", "created_at", "used"]
    list_filter   = ["used"]
    search_fields = ["user__email"]
    readonly_fields = ["token", "created_at"]
