from django.urls import path
from apps.assets.views import AssetListCreateView, AssetDetailView, AssetHistoryView

urlpatterns = [
    path("",              AssetListCreateView.as_view(), name="asset-list"),
    path("<uuid:pk>/",    AssetDetailView.as_view(),    name="asset-detail"),
    path("<uuid:pk>/history/", AssetHistoryView.as_view(), name="asset-history"),
]
