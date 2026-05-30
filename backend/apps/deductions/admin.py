from django.contrib import admin

from .models import Deduction


@admin.register(Deduction)
class DeductionAdmin(admin.ModelAdmin):
    list_display = ['farmer', 'cycle', 'deduction_type', 'amount', 'created_by', 'created_at']
    list_filter = ['deduction_type', 'cycle', 'cooperative']
    search_fields = ['farmer__first_name', 'farmer__last_name', 'farmer__member_number']
    readonly_fields = ['created_at']
