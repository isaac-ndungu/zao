from django.urls import path

from .views import ussd_callback, NotificationLogViewSet

notification_list = NotificationLogViewSet.as_view({'get': 'list'})
notification_detail = NotificationLogViewSet.as_view({'get': 'retrieve'})

api_urlpatterns = [
    path('notifications/', notification_list, name='notification-list'),
    path('notifications/<uuid:pk>/', notification_detail, name='notification-detail'),
]

callback_urlpatterns = [
    path('ussd/', ussd_callback, name='ussd-callback'),
]
