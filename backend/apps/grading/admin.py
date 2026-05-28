from django.contrib import admin

from .models import Grade, GradePrice


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = [
        'delivery', 'grade_letter', 'price_per_unit', 'rejection_reason',
        'is_overridden', 'created_at',
    ]
    list_filter = ['grade_letter', 'is_overridden']
    search_fields = ['delivery__batch_id', 'rejection_reason', 'override_reason']
    readonly_fields = ['is_overridden', 'overridden_at', 'created_at', 'updated_at']
    raw_id_fields = ['delivery', 'overridden_by', 'cooperative']


@admin.register(GradePrice)
class GradePriceAdmin(admin.ModelAdmin):
    list_display = ['grade_letter', 'price_per_unit', 'effective_from']
    list_filter = ['grade_letter', 'effective_from']
    search_fields = ['grade_letter']
