from django.contrib import admin

from .models import Notification, USSDMenuConfig, USSDSession


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'short_id', 'channel', 'notification_type', 'status',
        'recipient', 'cooperative', 'retry_count', 'sent_at',
    ]
    list_select_related = ['recipient', 'cooperative']
    list_filter = ['channel', 'notification_type', 'status', 'created_at']
    search_fields = [
        'content', 'external_id', 'error_message',
        'recipient__first_name', 'recipient__last_name',
        'recipient__phone_number',
    ]
    readonly_fields = [
        'id', 'external_id', 'sent_at', 'created_at',
    ]
    ordering = ['-created_at']

    @admin.display(description='ID')
    def short_id(self, obj):
        return str(obj.id)[:8]


@admin.register(USSDMenuConfig)
class USSDMenuConfigAdmin(admin.ModelAdmin):
    list_display = ['cooperative', 'menu_key', 'language', 'title', 'order', 'is_active']
    list_filter = ['language', 'is_active', 'menu_key']
    list_select_related = ['cooperative']
    search_fields = ['cooperative__name', 'menu_key', 'title']
    ordering = ['cooperative', 'order']


@admin.register(USSDSession)
class USSDSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'phone_number', 'farmer', 'current_menu', 'last_activity']
    list_select_related = ['farmer']
    list_filter = ['current_menu', 'last_activity']
    search_fields = ['session_id', 'phone_number', 'farmer__first_name', 'farmer__last_name']
    readonly_fields = ['session_id', 'phone_number', 'farmer', 'current_menu', 'last_activity']
    ordering = ['-last_activity']
