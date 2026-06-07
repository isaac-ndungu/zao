from django.contrib import admin

from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'role', 'truncated_content', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['session_id', 'content']

    @admin.display(description='content')
    def truncated_content(self, obj):
        return obj.content[:80] + ('...' if len(obj.content) > 80 else '')
