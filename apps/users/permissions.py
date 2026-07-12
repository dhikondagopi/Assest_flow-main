from rest_framework.permissions import BasePermission
from apps.users.models import User


def _role(user):
    """Safely get role from a user; returns empty string for anonymous."""
    return getattr(user, "role", "")


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and _role(request.user) == User.Role.ADMIN
        )


class IsAdminOrAssetManager(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and _role(request.user) in (User.Role.ADMIN, User.Role.ASSET_MANAGER)
        )


class IsAdminOrAssetManagerOrDeptHead(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and _role(request.user) in (
                User.Role.ADMIN,
                User.Role.ASSET_MANAGER,
                User.Role.DEPARTMENT_HEAD,
            )
        )


class IsDepartmentHead(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and _role(request.user) == User.Role.DEPARTMENT_HEAD
        )
