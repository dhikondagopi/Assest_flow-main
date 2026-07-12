from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.users.views import ForgotPasswordView, ResetPasswordView
from apps.compat.views import (
    CompatDepartmentListView,
    CompatCategoryListView,
    CompatEmployeeListView,
    CompatEmployeeRoleView,
    CompatAssetListView,
    CompatAssetDetailView,
    CompatAssetExportView,
    CompatAllocationListView,
    CompatAllocationExportView,
    CompatTransferListView,
    CompatTransferDetailView,
    CompatBookingListView,
    CompatBookingExportView,
    CompatMaintenanceListView,
    CompatMaintenanceDetailView,
    CompatMaintenanceExportView,
    CompatNotificationListView,
    CompatNotificationReadView,
    CompatNotificationReadAllView,
    CompatUnreadCountView,
)

urlpatterns = [
    # Auth
    path("auth/login/",              TokenObtainPairView.as_view(),  name="compat-login"),
    path("auth/refresh/",            TokenRefreshView.as_view(),     name="compat-refresh"),
    path("auth/forgot-password/",    ForgotPasswordView.as_view(),   name="compat-forgot-password"),
    path("auth/reset-password/",     ResetPasswordView.as_view(),    name="compat-reset-password"),

    # Org
    path("departments/",        CompatDepartmentListView.as_view(),  name="compat-departments"),
    path("categories/",         CompatCategoryListView.as_view(),    name="compat-categories"),
    path("employees/",          CompatEmployeeListView.as_view(),    name="compat-employees"),
    path("employees/<uuid:pk>/role/", CompatEmployeeRoleView.as_view(), name="compat-employee-role"),

    # Assets
    path("assets/",             CompatAssetListView.as_view(),       name="compat-assets"),
    path("assets/export/",      CompatAssetExportView.as_view(),     name="compat-assets-export"),
    path("assets/<uuid:pk>/",   CompatAssetDetailView.as_view(),     name="compat-asset-detail"),

    # Allocations
    path("allocations/",        CompatAllocationListView.as_view(),  name="compat-allocations"),
    path("allocations/export/", CompatAllocationExportView.as_view(),name="compat-allocations-export"),

    # Transfers
    path("transfers/",          CompatTransferListView.as_view(),       name="compat-transfers"),
    path("transfers/<uuid:pk>/",CompatTransferDetailView.as_view(),     name="compat-transfer-detail"),

    # Bookings
    path("bookings/",           CompatBookingListView.as_view(),     name="compat-bookings"),
    path("bookings/export/",    CompatBookingExportView.as_view(),   name="compat-bookings-export"),

    # Maintenance
    path("maintenance/",           CompatMaintenanceListView.as_view(),    name="compat-maintenance"),
    path("maintenance/export/",    CompatMaintenanceExportView.as_view(),  name="compat-maintenance-export"),
    path("maintenance/<uuid:pk>/", CompatMaintenanceDetailView.as_view(), name="compat-maintenance-detail"),

    # Notifications
    path("notifications/",                    CompatNotificationListView.as_view(),    name="compat-notifications"),
    path("notifications/read-all/",           CompatNotificationReadAllView.as_view(), name="compat-notif-read-all"),
    path("notifications/unread-count/",       CompatUnreadCountView.as_view(),         name="compat-notif-unread-count"),
    path("notifications/<uuid:pk>/read/",     CompatNotificationReadView.as_view(),    name="compat-notif-read"),
]
