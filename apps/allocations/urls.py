from django.urls import path
from apps.allocations.views import (
    AllocationListCreateView,
    AllocationDetailView,
    ReturnAllocationView,
    OverdueAllocationsView,
    TransferRequestListCreateView,
    TransferRequestDetailView,
    ApproveTransferView,
    RejectTransferView,
)

urlpatterns = [
    path("",                             AllocationListCreateView.as_view(),  name="allocation-list"),
    path("overdue/",                     OverdueAllocationsView.as_view(),    name="allocation-overdue"),
    path("<uuid:pk>/",                   AllocationDetailView.as_view(),      name="allocation-detail"),
    path("<uuid:pk>/return/",            ReturnAllocationView.as_view(),      name="allocation-return"),

    path("transfers/",                   TransferRequestListCreateView.as_view(), name="transfer-list"),
    path("transfers/<uuid:pk>/",         TransferRequestDetailView.as_view(),     name="transfer-detail"),
    path("transfers/<uuid:pk>/approve/", ApproveTransferView.as_view(),           name="transfer-approve"),
    path("transfers/<uuid:pk>/reject/",  RejectTransferView.as_view(),            name="transfer-reject"),
]
