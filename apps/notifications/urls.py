from django.urls import path
from apps.notifications.views import (
    NotificationListView,
    MarkNotificationReadView,
    MarkAllNotificationsReadView,
    UnreadCountView,
)

urlpatterns = [
    path("",                  NotificationListView.as_view(),        name="notification-list"),
    path("read-all/",         MarkAllNotificationsReadView.as_view(), name="notification-read-all"),
    path("unread-count/",     UnreadCountView.as_view(),              name="notification-unread-count"),
    path("<uuid:pk>/read/",   MarkNotificationReadView.as_view(),     name="notification-read"),
]
