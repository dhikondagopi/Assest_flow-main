from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """GET /api/notifications/ — current user's notifications, newest first."""
    serializer_class   = NotificationSerializer
    permission_classes = [IsAuthenticated]
    ordering           = ["-created_at"]

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user)
        # Optional filter: ?unread=true
        if self.request.query_params.get("unread") == "true":
            qs = qs.filter(is_read=False)
        return qs


class MarkNotificationReadView(APIView):
    """POST /api/notifications/<id>/read/ — mark single notification read."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notif = Notification.objects.get(pk=pk, recipient=request.user)
        except Notification.DoesNotExist:
            return Response({"detail": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)

        notif.is_read = True
        notif.save(update_fields=["is_read"])
        return Response({"message": "Marked as read."})


class MarkAllNotificationsReadView(APIView):
    """POST /api/notifications/read-all/ — bulk mark all unread as read."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True)
        return Response({"message": f"{count} notification(s) marked as read."})


class UnreadCountView(APIView):
    """GET /api/notifications/unread-count/ — quick badge count."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"unread_count": count})
