import uuid
from decimal import Decimal

from django.contrib.postgres.indexes import BrinIndex
from django.db import models


class PeriodType(models.TextChoices):
    DAILY = 'DAILY', 'Daily'
    WEEKLY = 'WEEKLY', 'Weekly'
    MONTHLY = 'MONTHLY', 'Monthly'
    YEARLY = 'YEARLY', 'Yearly'


class AnalyticsSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cooperative = models.ForeignKey(
        'cooperatives.Cooperative', on_delete=models.CASCADE,
        related_name='analytics_snapshots',
    )
    period_type = models.CharField(
        max_length=10, choices=PeriodType.choices, db_index=True,
    )
    period_start = models.DateField(db_index=True)
    period_end = models.DateField()
    schema_version = models.IntegerField(default=1)
    data = models.JSONField(default=dict, blank=True)
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-period_start']
        unique_together = [('cooperative', 'period_type', 'period_start')]
        indexes = [
            models.Index(fields=['cooperative', 'period_type', '-period_start']),
            BrinIndex(fields=['computed_at'], pages_per_range=32),
        ]

    def __str__(self):
        return f'{self.cooperative} — {self.period_type} {self.period_start}'


class MaterializedAnalytics(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    period_type = models.CharField(
        max_length=10, choices=PeriodType.choices, db_index=True,
    )
    period_start = models.DateField(db_index=True)
    period_end = models.DateField()
    schema_version = models.IntegerField(default=1)
    data = models.JSONField(default=dict, blank=True)
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-period_start']
        verbose_name_plural = 'materialized analytics'
        unique_together = [('period_type', 'period_start')]

    def __str__(self):
        return f'Global — {self.period_type} {self.period_start}'


class ExportStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    PROCESSING = 'PROCESSING', 'Processing'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'


class AnalyticsExportTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cooperative = models.ForeignKey(
        'cooperatives.Cooperative', on_delete=models.CASCADE,
        null=True, blank=True, related_name='analytics_exports',
    )
    requested_by = models.ForeignKey(
        'auth_api.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='analytics_exports',
    )
    export_type = models.CharField(max_length=50)
    params = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20, choices=ExportStatus.choices, default=ExportStatus.PENDING,
    )
    celery_task_id = models.CharField(max_length=255, blank=True, default='')
    download_url = models.URLField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    row_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.export_type} export ({self.get_status_display()})'
