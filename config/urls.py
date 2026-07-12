from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path("admin/", admin.site.urls),

    # OpenAPI schema + Swagger UI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # App routes
    path("api/auth/",         include("apps.users.urls")),
    path("api/org/",          include("apps.org.urls")),
    path("api/assets/",       include("apps.assets.urls")),
    path("api/allocations/",  include("apps.allocations.urls")),
    path("api/bookings/",     include("apps.bookings.urls")),
    path("api/maintenance/",  include("apps.maintenance.urls")),
    path("api/notifications/",include("apps.notifications.urls")),
    path("api/dashboard/",    include("apps.dashboard.urls")),
    path("api/v1/",           include("apps.compat.urls")),   # frontend-compatible flat API
]
