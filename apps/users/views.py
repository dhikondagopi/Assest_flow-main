from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.users.models import PasswordResetToken
from apps.users.permissions import IsAdmin
from apps.users.serializers import (
    ForgotPasswordSerializer,
    PromoteEmployeeSerializer,
    ResetPasswordSerializer,
    SignupSerializer,
    UserMeSerializer,
)

User = get_user_model()


# ── Custom throttle: 3 forgot-password requests per hour per IP ───────────────
class ForgotPasswordThrottle(AnonRateThrottle):
    rate = "3/hour"
    scope = "forgot_password"


class SignupView(generics.CreateAPIView):
    """POST /api/auth/signup/ — public, creates EMPLOYEE account."""
    serializer_class = SignupSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"message": "Account created successfully.", "id": str(user.id), "email": user.email},
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/auth/me/ — authenticated user's own profile."""
    serializer_class = UserMeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ForgotPasswordView(APIView):
    """
    POST /api/auth/forgot-password/
    Rate-limited to 3/hour per IP. Sends a 15-minute reset token to console email backend.
    Always returns 200 to prevent email enumeration.
    """
    permission_classes = [AllowAny]
    throttle_classes   = [ForgotPasswordThrottle]

    # Token TTL: 15 minutes (override PASSWORD_RESET_TIMEOUT_HOURS for forgot-pw flow)
    TOKEN_TTL_MINUTES = 15

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        # Always return 200 to avoid email enumeration
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return Response({"message": "If that email exists, a reset link has been sent."})

        # Invalidate any existing unused tokens for this user
        PasswordResetToken.objects.filter(user=user, used=False).update(used=True)

        token_obj = PasswordResetToken.objects.create(user=user)
        # Support both 5173 (original) and 8080 (current dev port)
        frontend_origin = request.META.get("HTTP_ORIGIN", "http://localhost:8080")
        reset_url = f"{frontend_origin}/reset-password?token={token_obj.token}"

        send_mail(
            subject="AssetFlow – Reset your password",
            message=(
                f"Click the link below to reset your password.\n"
                f"This link expires in {self.TOKEN_TTL_MINUTES} minutes.\n\n"
                f"{reset_url}\n\n"
                f"If you did not request this, ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
        return Response({"message": "If that email exists, a reset link has been sent."})


class ResetPasswordView(APIView):
    """POST /api/auth/reset-password/ — validates token & sets new password."""
    permission_classes = [AllowAny]
    TOKEN_TTL_MINUTES  = 15

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_val = serializer.validated_data["token"]
        new_pass  = serializer.validated_data["password"]

        try:
            token_obj = PasswordResetToken.objects.select_related("user").get(
                token=token_val, used=False
            )
        except PasswordResetToken.DoesNotExist:
            return Response(
                {"code": "INVALID_TOKEN", "detail": "Invalid or already-used reset token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expiry = token_obj.created_at + timedelta(minutes=self.TOKEN_TTL_MINUTES)
        if timezone.now() > expiry:
            token_obj.used = True
            token_obj.save(update_fields=["used"])
            return Response(
                {"code": "TOKEN_EXPIRED", "detail": "Reset token has expired. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = token_obj.user
        user.set_password(new_pass)
        user.save(update_fields=["password"])
        token_obj.used = True
        token_obj.save(update_fields=["used"])

        return Response({"message": "Password reset successfully. You can now sign in."})


class PromoteEmployeeView(APIView):
    """PATCH /api/auth/users/<id>/promote/ — Admin only; sole path to change role."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = PromoteEmployeeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_role = serializer.validated_data["role"]

        if user.pk == request.user.pk:
            return Response(
                {"detail": "You cannot change your own role."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.role = new_role
        user.save(update_fields=["role"])
        return Response(
            {"message": f"{user.get_full_name()} promoted to {new_role}.", "role": new_role}
        )


class UserListView(generics.ListAPIView):
    """GET /api/auth/users/ — Admin only; list all users."""
    serializer_class = UserMeSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = User.objects.all()
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["first_name", "last_name", "role", "created_at"]


class SignupView(generics.CreateAPIView):
    """POST /api/auth/signup/ — public, creates EMPLOYEE account."""
    serializer_class = SignupSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"message": "Account created successfully.", "id": str(user.id), "email": user.email},
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/auth/me/ — authenticated user's own profile."""
    serializer_class = UserMeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ForgotPasswordView(APIView):
    """POST /api/auth/forgot-password/ — sends reset link to console."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        # Always return 200 to avoid email enumeration
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return Response({"message": "If that email exists, a reset link has been sent."})

        token_obj = PasswordResetToken.objects.create(user=user)
        reset_url = f"http://localhost:5173/reset-password?token={token_obj.token}"

        send_mail(
            subject="AssetFlow – Reset your password",
            message=f"Click the link to reset your password (valid {settings.PASSWORD_RESET_TIMEOUT_HOURS}h):\n{reset_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
        return Response({"message": "If that email exists, a reset link has been sent."})


class ResetPasswordView(APIView):
    """POST /api/auth/reset-password/ — validates token & sets new password."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_val = serializer.validated_data["token"]
        new_pass  = serializer.validated_data["password"]

        try:
            token_obj = PasswordResetToken.objects.select_related("user").get(
                token=token_val, used=False
            )
        except PasswordResetToken.DoesNotExist:
            return Response(
                {"detail": "Invalid or expired reset token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        timeout_hours = getattr(settings, "PASSWORD_RESET_TIMEOUT_HOURS", 24)
        expiry = token_obj.created_at + timedelta(hours=timeout_hours)
        if timezone.now() > expiry:
            return Response(
                {"detail": "Reset token has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = token_obj.user
        user.set_password(new_pass)
        user.save(update_fields=["password"])
        token_obj.used = True
        token_obj.save(update_fields=["used"])

        return Response({"message": "Password reset successfully."})


class PromoteEmployeeView(APIView):
    """PATCH /api/auth/users/<id>/promote/ — Admin only; sole path to change role."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = PromoteEmployeeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_role = serializer.validated_data["role"]

        if user.pk == request.user.pk:
            return Response(
                {"detail": "You cannot change your own role."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.role = new_role
        user.save(update_fields=["role"])
        return Response(
            {"message": f"{user.get_full_name()} promoted to {new_role}.", "role": new_role}
        )


class UserListView(generics.ListAPIView):
    """GET /api/auth/users/ — Admin only; list all users."""
    serializer_class = UserMeSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = User.objects.all()
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["first_name", "last_name", "role", "created_at"]
