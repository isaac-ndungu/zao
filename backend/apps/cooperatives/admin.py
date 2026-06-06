from django.contrib import admin
from django.utils.html import format_html
from apps.cooperatives.models import Cooperative


@admin.register(Cooperative)
class CooperativeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'registration_number', 'county', 'sub_county',
        'produce_type', 'payment_model', 'is_active', 'is_verified',
        'member_count', 'logo_preview',
    ]
    list_filter = [
        'produce_type', 'payment_model', 'is_active', 'is_verified',
        'county', 'sub_county',
    ]
    search_fields = ['name', 'registration_number', 'kra_pin']
    readonly_fields = ['created_at', 'updated_at', 'logo_preview']

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height: 40px; max-width: 60px;" />',
                obj.logo.url,
            )
        return ''
    logo_preview.short_description = 'Logo'
