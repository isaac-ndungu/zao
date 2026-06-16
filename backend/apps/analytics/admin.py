from django.contrib import admin

from .models import AnalyticsExportTask, AnalyticsSnapshot, MaterializedAnalytics


@admin.register(AnalyticsSnapshot)
class AnalyticsSnapshotAdmin(admin.ModelAdmin):
    list_display = ['cooperative', 'period_type', 'period_start', 'period_end',
                    'schema_version', 'computed_at']
    list_filter = ['period_type', 'cooperative']
    date_hierarchy = 'period_start'
    readonly_fields = ['computed_at']


@admin.register(MaterializedAnalytics)
class MaterializedAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['period_type', 'period_start', 'period_end',
                    'schema_version', 'computed_at']
    list_filter = ['period_type']
    date_hierarchy = 'period_start'
    readonly_fields = ['computed_at']


@admin.register(AnalyticsExportTask)
class AnalyticsExportTaskAdmin(admin.ModelAdmin):
    list_display = ['export_type', 'status', 'requested_by', 'cooperative',
                    'row_count', 'created_at', 'completed_at']
    list_filter = ['status', 'export_type']
    readonly_fields = ['created_at', 'completed_at']
