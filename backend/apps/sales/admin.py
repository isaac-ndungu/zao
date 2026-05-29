from django.contrib import admin

from .models import Buyer, PaymentCycle, Sale


@admin.register(Buyer)
class BuyerAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone_number', 'email', 'is_active', 'cooperative']
    list_filter = ['is_active', 'cooperative']
    search_fields = ['name', 'contact_person', 'kra_pin']


@admin.register(PaymentCycle)
class PaymentCycleAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_closed', 'cooperative']
    list_filter = ['is_closed', 'cooperative']
    search_fields = ['name']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'buyer', 'grade_name', 'quantity',
        'total_amount', 'sale_date', 'cooperative',
    ]
    list_filter = ['sale_date', 'cooperative']
    search_fields = ['invoice_number', 'buyer__name']
    readonly_fields = ['total_amount', 'created_at', 'updated_at']

    def grade_name(self, obj):
        return obj.grade.grade_letter
    grade_name.short_description = 'Grade'
