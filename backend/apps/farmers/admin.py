from django.contrib import admin

from apps.farmers.models import Farmer


@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = [
        'member_number', 'first_name', 'last_name', 'phone_number',
        'payment_method', 'is_active', 'cooperative',
    ]
    list_filter = ['payment_method', 'is_active', 'county']
    list_select_related = ['cooperative']
    search_fields = [
        'member_number', 'first_name', 'last_name', 'phone_number',
    ]
    readonly_fields = ['member_number', 'date_joined', 'updated_at']
