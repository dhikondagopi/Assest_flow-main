from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView

from apps.users.views import (
    SignupView,
    MeView,
    ForgotPasswordView,
    ResetPasswordView,
    PromoteEmployeeView,
    UserListView,
)

urlpatterns = [
    path("signup/",         SignupView.as_view(),         name="auth-signup"),
    path("login/",          TokenObtainPairView.as_view(), name="auth-login"),
    path("token/refresh/",  TokenRefreshView.as_view(),    name="auth-token-refresh"),
    path("logout/",         TokenBlacklistView.as_view(),  name="auth-logout"),
    path("me/",             MeView.as_view(),              name="auth-me"),
    path("forgot-password/",ForgotPasswordView.as_view(),  name="auth-forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(),   name="auth-reset-password"),
    path("users/",          UserListView.as_view(),        name="auth-user-list"),
    path("users/<uuid:pk>/promote/", PromoteEmployeeView.as_view(), name="auth-promote"),
]
