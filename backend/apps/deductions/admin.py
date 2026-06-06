from django.contrib import admin

from .models import Deduction, FarmInputCredit


@admin.register(Deduction)
class DeductionAdmin(admin.ModelAdmin):
    list_display = ['farmer', 'cycle', 'deduction_type', 'amount', 'created_by', 'created_at']
    list_select_related = ['farmer', 'cycle', 'created_by']
    list_filter = ['deduction_type', 'cycle', 'cooperative']
    search_fields = ['farmer__first_name', 'farmer__last_name', 'farmer__member_number']
    readonly_fields = ['created_at']


@admin.register(FarmInputCredit)
class FarmInputCreditAdmin(admin.ModelAdmin):
    list_display = ['farmer', 'item_description', 'amount', 'installment_amount', 'total_deducted', 'status', 'supplied_date']
    list_select_related = ['farmer']
    list_filter = ['status', 'cooperative']
    search_fields = ['farmer__first_name', 'farmer__last_name', 'item_description']
