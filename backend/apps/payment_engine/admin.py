from django.contrib import admin

from .models import FarmerPayment, PaymentCycle


@admin.register(PaymentCycle)
class PaymentCycleAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'status', 'cooperative']
    list_select_related = ['cooperative']
    list_filter = ['status', 'cooperative']
    search_fields = ['name']
    readonly_fields = ['status', 'totals', 'locked_by', 'locked_at', 'computed_at']


@admin.register(FarmerPayment)
class FarmerPaymentAdmin(admin.ModelAdmin):
    list_display = ['farmer', 'cycle', 'total_quantity', 'gross_amount', 'net_amount', 'cooperative']
    list_select_related = ['farmer', 'cycle', 'cooperative']
    list_filter = ['cycle', 'cooperative']
    search_fields = ['farmer__first_name', 'farmer__last_name', 'farmer__member_number']
    readonly_fields = ['total_quantity', 'grade_breakdown', 'gross_amount', 'deductions', 'net_amount', 'computation_log']
