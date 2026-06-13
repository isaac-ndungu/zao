from django.contrib import admin

from .models import LegalDocument, LegalAcceptance


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ['slug', 'title', 'version', 'is_active', 'requires_acceptance', 'published_at']
    list_filter = ['is_active', 'requires_acceptance', 'slug']
    search_fields = ['slug', 'title']
    prepopulated_fields = {'slug': ('title',)}
    ordering = ['-published_at', '-version']


@admin.register(LegalAcceptance)
class LegalAcceptanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'document', 'version', 'accepted_at']
    list_filter = ['document__slug', 'accepted_at']
    search_fields = ['user__email']
    date_hierarchy = 'accepted_at'
    readonly_fields = ['user', 'document', 'version', 'accepted_at', 'ip_address', 'user_agent']
