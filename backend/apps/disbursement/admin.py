from django.contrib import admin

from .models import DisbursementBatch, DisbursementTransaction


class DisbursementTransactionInline(admin.TabularInline):
    model = DisbursementTransaction
    extra = 0
    readonly_fields = [
        'amount', 'payment_method', 'status', 'transaction_id',
        'result_code', 'result_desc', 'retry_count',
    ]


@admin.register(DisbursementBatch)
class DisbursementBatchAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'payment_cycle', 'status', 'command_id', 'total_amount',
        'total_transactions', 'successful_count', 'failed_count',
        'approved_by', 'created_by', 'created_at',
    ]
    list_select_related = ['payment_cycle', 'approved_by', 'created_by']
    list_filter = ['status', 'command_id', 'cooperative']
    search_fields = ['id', 'conversation_id']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [DisbursementTransactionInline]


@admin.register(DisbursementTransaction)
class DisbursementTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'farmer', 'amount', 'payment_method', 'status',
        'transaction_id', 'retry_count', 'created_at',
    ]
    list_select_related = ['farmer']
    list_filter = ['status', 'payment_method', 'batch__cooperative']
    search_fields = ['farmer__first_name', 'farmer__last_name', 'transaction_id', 'conversation_id']
    readonly_fields = ['created_at']
