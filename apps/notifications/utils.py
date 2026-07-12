from apps.notifications.models import Notification


def create_notification(recipient, verb: str, message: str, target_id: str = ""):
    """
    Utility called from other apps to create a notification.
    Safe to call inside transactions — does not commit independently.
    """
    Notification.objects.create(
        recipient=recipient,
        verb=verb,
        message=message,
        target_id=target_id,
    )
