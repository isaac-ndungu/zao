from django.contrib import admin

from .models import ChatbotConfig, ChatMessage


@admin.register(ChatbotConfig)
class ChatbotConfigAdmin(admin.ModelAdmin):
    list_display = ['version', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'created_at']
    readonly_fields = ['version', 'created_at']

    def save_model(self, request, obj, form, change):
        if not change:
            ChatbotConfig.objects.publish_new(obj.system_prompt, request.user)
        else:
            super().save_model(request, obj, form, change)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'role', 'truncated_content', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['session_id', 'content']

    @admin.display(description='content')
    def truncated_content(self, obj):
        return obj.content[:80] + ('...' if len(obj.content) > 80 else '')
