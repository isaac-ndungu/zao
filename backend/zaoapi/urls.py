"""
URL configuration for zaoapi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from apps.base.health import health_check, health_ping
from apps.base.views.global_search import GlobalSearchView
from apps.disbursement.callbacks import mpesa_result_callback, mpesa_timeout_callback
from apps.notifications.urls import api_urlpatterns, callback_urlpatterns as notification_callback_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),

    # Infrastructure (unversioned)
    path('api/health/', health_check, name='health-check'),
    path('api/health/ping/', health_ping, name='health-ping'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/search/', GlobalSearchView.as_view(), name='global-search'),

    # External webhooks (unversioned — URLs registered in third-party developer portals)
    path('api/callback/mpesa/result/', mpesa_result_callback),
    path('api/callback/mpesa/timeout/', mpesa_timeout_callback),
    path('api/callback/', include(notification_callback_urlpatterns)),

    # App routes — unversioned legacy prefix (kept for backward compatibility)
    path('api/', include('apps.cooperatives.urls')),
    path('api/', include('apps.users.urls')),
    path('api/', include('apps.farmers.urls')),
    path('api/', include('apps.deliveries.urls')),
    path('api/', include('apps.grading.urls')),
    path('api/', include('apps.inventory.urls')),
    path('api/', include('apps.auth_api.urls')),
    path('api/', include('apps.routes.urls')),
    path('api/', include('apps.sales.urls')),
    path('api/', include('apps.payment_engine.urls')),
    path('api/deductions/', include('apps.deductions.urls')),
    path('api/loans/', include('apps.loans.urls')),
    path('api/disbursements/', include('apps.disbursement.urls')),
    path('api/statements/', include('apps.statements.urls')),
    path('api/chat/', include('apps.chat.urls')),
    path('api/', include(api_urlpatterns)),
    path('api/', include('apps.legal.urls')),
    path('api/', include('apps.analytics.urls')),

    # App routes — versioned v1 prefix (same views, new canonical path)
    path('api/v1/', include('apps.cooperatives.urls')),
    path('api/v1/', include('apps.users.urls')),
    path('api/v1/', include('apps.farmers.urls')),
    path('api/v1/', include('apps.deliveries.urls')),
    path('api/v1/', include('apps.grading.urls')),
    path('api/v1/', include('apps.inventory.urls')),
    path('api/v1/', include('apps.auth_api.urls')),
    path('api/v1/', include('apps.routes.urls')),
    path('api/v1/', include('apps.sales.urls')),
    path('api/v1/', include('apps.payment_engine.urls')),
    path('api/v1/deductions/', include('apps.deductions.urls')),
    path('api/v1/loans/', include('apps.loans.urls')),
    path('api/v1/disbursements/', include('apps.disbursement.urls')),
    path('api/v1/statements/', include('apps.statements.urls')),
    path('api/v1/chat/', include('apps.chat.urls')),
    path('api/v1/', include(api_urlpatterns)),
    path('api/v1/', include('apps.legal.urls')),
    path('api/v1/', include('apps.analytics.urls')),
]

if settings.SUPERADMIN_ENABLED:
    urlpatterns.append(path('api/admin/', include('apps.admin.urls')))
    urlpatterns.append(path('api/v1/admin/', include('apps.admin.urls')))
