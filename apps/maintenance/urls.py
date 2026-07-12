from django.urls import path
from apps.maintenance.views import (
    MaintenanceRequestListCreateView,
    MaintenanceRequestDetailView,
    ApproveMaintenanceView,
    StartMaintenanceView,
    ResolveMaintenanceView,
    RejectMaintenanceView,
)

urlpatterns = [
    path("",                        MaintenanceRequestListCreateView.as_view(), name="maintenance-list"),
    path("<uuid:pk>/",              MaintenanceRequestDetailView.as_view(),     name="maintenance-detail"),
    path("<uuid:pk>/approve/",      ApproveMaintenanceView.as_view(),           name="maintenance-approve"),
    path("<uuid:pk>/start/",        StartMaintenanceView.as_view(),             name="maintenance-start"),
    path("<uuid:pk>/resolve/",      ResolveMaintenanceView.as_view(),           name="maintenance-resolve"),
    path("<uuid:pk>/reject/",       RejectMaintenanceView.as_view(),            name="maintenance-reject"),
]
