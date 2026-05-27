from django.contrib import admin
from apps.cooperatives.models import Cooperative


@admin.register(Cooperative)
class CooperativeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'registration_number', 'county',
        'produce_type', 'payment_model', 'is_active',
    ]
    list_filter = ['produce_type', 'payment_model', 'is_active', 'county']
    search_fields = ['name', 'registration_number']
