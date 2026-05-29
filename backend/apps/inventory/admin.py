from django.contrib import admin

from .models import Inventory


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = [
        'batch_id', 'product_type', 'grade', 'unit',
        'quantity_in', 'quantity_out', 'is_sold', 'created_at',
    ]
    list_filter = ['product_type', 'grade', 'unit']
    search_fields = ['batch_id', 'grade']
    readonly_fields = [
        'batch_id', 'product_type', 'grade', 'unit',
        'quantity_in', 'quantity_out', 'created_at', 'updated_at',
    ]
