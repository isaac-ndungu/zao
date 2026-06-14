from django.urls import path

from apps.auth_api.views import (
    Disable2FAView,
    Enable2FAView,
    FarmerRequestOTPView,
    FarmerVerifyOTPView,
    InviteView,
    InviteAcceptView,
    LoginView,
    LogoutView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
    RequestOTPView,
    TokenRefreshView,
    VerifyOTPView,
)

urlpatterns = [
    path('auth/login/', LoginView.as_view()),
    path('auth/2fa/request/', RequestOTPView.as_view()),
    path('auth/2fa/verify/', VerifyOTPView.as_view()),
    path('auth/farmer/request/', FarmerRequestOTPView.as_view()),
    path('auth/farmer/verify/', FarmerVerifyOTPView.as_view()),
    path('auth/refresh/', TokenRefreshView.as_view()),
    path('auth/logout/', LogoutView.as_view()),
    path('auth/invite/', InviteView.as_view()),
    path('auth/invite/accept/', InviteAcceptView.as_view()),
    path('auth/password-reset/request/', PasswordResetRequestView.as_view()),
    path('auth/password-reset/verify/', PasswordResetVerifyView.as_view()),
    path('auth/2fa/enable/', Enable2FAView.as_view()),
    path('auth/2fa/disable/', Disable2FAView.as_view()),
]
