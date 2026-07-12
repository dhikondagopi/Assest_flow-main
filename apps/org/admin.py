from django.contrib import admin
from apps.org.models import AssetCategory, Department, EmployeeProfile


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display  = ["name", "code", "parent", "head", "created_at"]
    list_filter   = ["parent"]
    search_fields = ["name", "code"]
    raw_id_fields = ["parent", "head"]


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display  = ["name", "created_at"]
    search_fields = ["name"]


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display  = ["user", "department", "employee_number", "phone"]
    list_filter   = ["department"]
    search_fields = ["user__email", "user__first_name", "employee_number"]
    raw_id_fields = ["user", "department"]
