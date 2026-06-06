from django.contrib import admin

from apps.farmers.models import Farmer


@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = [
        'first_name', 'last_name', 'phone_number',
        'is_active', 'cooperative',
    ]
    list_filter = ['is_active', 'county']
    list_select_related = ['cooperative']
    search_fields = [
        'first_name', 'last_name', 'phone_number',
    ]
    readonly_fields = ['date_joined', 'updated_at']
