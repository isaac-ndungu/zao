from django.urls import path

from apps.auth_api.views import (
    FarmerRequestOTPView,
    FarmerVerifyOTPView,
    InviteView,
    InviteAcceptView,
    LoginView,
    LogoutView,
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
]
