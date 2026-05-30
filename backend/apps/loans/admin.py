from django.contrib import admin

from .models import Loan, LoanRepayment


class LoanRepaymentInline(admin.TabularInline):
    model = LoanRepayment
    extra = 0
    readonly_fields = ['amount', 'created_at']


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = [
        'farmer', 'amount_principal', 'status', 'installments_paid',
        'number_of_installments', 'approved_at', 'disbursed_at', 'created_at',
    ]
    list_filter = ['status', 'cooperative']
    search_fields = ['farmer__first_name', 'farmer__last_name', 'farmer__member_number']
    readonly_fields = ['created_at']
    inlines = [LoanRepaymentInline]


@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = ['loan', 'amount', 'created_at']
    list_filter = ['loan__status']
