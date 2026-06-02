from django.contrib import admin

from .models import Delivery


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = [
        'batch_id', 'farmer', 'product_type', 'quantity_kg',
        'volume_litres', 'status', 'date_delivered', 'shift',
    ]
    list_select_related = ['farmer', 'grader']
    list_filter = ['product_type', 'status', 'shift', 'date_delivered']
    search_fields = ['batch_id', 'farmer__first_name', 'farmer__last_name', 'farmer__member_number']
    readonly_fields = ['batch_id', 'date_delivered', 'updated_at']
    raw_id_fields = ['farmer', 'grader']
