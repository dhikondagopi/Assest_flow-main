from django.urls import path
from apps.org.views import (
    DepartmentListCreateView,
    DepartmentDetailView,
    DepartmentTreeView,
    AssetCategoryListCreateView,
    AssetCategoryDetailView,
    EmployeeProfileListView,
    EmployeeProfileDetailView,
)

urlpatterns = [
    path("departments/",           DepartmentListCreateView.as_view(), name="dept-list"),
    path("departments/tree/",      DepartmentTreeView.as_view(),       name="dept-tree"),
    path("departments/<uuid:pk>/", DepartmentDetailView.as_view(),     name="dept-detail"),

    path("categories/",            AssetCategoryListCreateView.as_view(), name="category-list"),
    path("categories/<uuid:pk>/",  AssetCategoryDetailView.as_view(),     name="category-detail"),

    path("employees/",             EmployeeProfileListView.as_view(),    name="employee-list"),
    path("employees/<uuid:pk>/",   EmployeeProfileDetailView.as_view(),  name="employee-detail"),
]
