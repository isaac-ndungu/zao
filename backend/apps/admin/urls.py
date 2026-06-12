from django.urls import path

from apps.admin.views import (
    AdminAuditLogView,
    AdminCeleryTasksView,
    AdminCooperativeActivateView,
    AdminCooperativeDeactivateView,
    AdminCooperativeViewSet,
    AdminDashboardView,
    AdminHealthView,
    AdminUserActivateView,
    AdminUserDeactivateView,
    AdminUserForceLogoutView,
    AdminUserResetPasswordView,
    AdminUserToggle2FAView,
    AdminUserViewSet,
    CreateSuperUserView,
    ImpersonateView,
)

urlpatterns = [
    path('users/create-superuser/', CreateSuperUserView.as_view()),
    path('users/', AdminUserViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('users/<uuid:pk>/', AdminUserViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),
    path('users/<uuid:pk>/activate/', AdminUserActivateView.as_view()),
    path('users/<uuid:pk>/deactivate/', AdminUserDeactivateView.as_view()),
    path('users/<uuid:pk>/reset-password/', AdminUserResetPasswordView.as_view()),
    path('users/<uuid:pk>/toggle-2fa/', AdminUserToggle2FAView.as_view()),
    path('users/<uuid:pk>/force-logout/', AdminUserForceLogoutView.as_view()),
    path('impersonate/<uuid:user_id>/', ImpersonateView.as_view()),
    path('cooperatives/', AdminCooperativeViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('cooperatives/<uuid:pk>/', AdminCooperativeViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),
    path('cooperatives/<uuid:pk>/activate/', AdminCooperativeActivateView.as_view()),
    path('cooperatives/<uuid:pk>/deactivate/', AdminCooperativeDeactivateView.as_view()),
    path('dashboard/', AdminDashboardView.as_view()),
    path('audit-logs/', AdminAuditLogView.as_view()),
    path('health/', AdminHealthView.as_view()),
    path('celery/tasks/', AdminCeleryTasksView.as_view()),
]
