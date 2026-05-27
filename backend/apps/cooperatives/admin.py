from django.contrib import admin
from apps.cooperatives.models import Cooperative


@admin.register(Cooperative)
class CooperativeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'registration_number', 'county', 'sub_county',
        'produce_type', 'payment_model', 'is_active', 'is_verified',
        'member_count',
    ]
    list_filter = [
        'produce_type', 'payment_model', 'is_active', 'is_verified',
        'county', 'sub_county',
    ]
    search_fields = ['name', 'registration_number', 'kra_pin']
    readonly_fields = ['created_at', 'updated_at']
