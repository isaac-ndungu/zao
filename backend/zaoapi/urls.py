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
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from apps.base.health import health_check
from apps.disbursement.callbacks import mpesa_result_callback, mpesa_timeout_callback
from apps.notifications.urls import api_urlpatterns, callback_urlpatterns as notification_callback_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health-check'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
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
    path('api/callback/mpesa/result/', mpesa_result_callback),
    path('api/callback/mpesa/timeout/', mpesa_timeout_callback),
    path('api/callback/', include(notification_callback_urlpatterns)),
    path('api/', include(api_urlpatterns)),
]
