from django.urls import path

from .views import ussd_callback, NotificationLogViewSet, ContactMessageViewSet, ContactMessageAdminViewSet

notification_list = NotificationLogViewSet.as_view({'get': 'list'})
notification_detail = NotificationLogViewSet.as_view({'get': 'retrieve'})
contact_create = ContactMessageViewSet.as_view({'post': 'create'})
contact_admin_list = ContactMessageAdminViewSet.as_view({'get': 'list'})
contact_admin_detail = ContactMessageAdminViewSet.as_view({'get': 'retrieve'})

api_urlpatterns = [
    path('notifications/', notification_list, name='notification-list'),
    path('notifications/<uuid:pk>/', notification_detail, name='notification-detail'),
    path('contact/', contact_create, name='contact-create'),
    path('contact/messages/', contact_admin_list, name='contact-admin-list'),
    path('contact/messages/<uuid:pk>/', contact_admin_detail, name='contact-admin-detail'),
]

callback_urlpatterns = [
    path('ussd/', ussd_callback, name='ussd-callback'),
]
