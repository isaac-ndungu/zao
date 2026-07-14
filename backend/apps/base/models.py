from django.conf import settings
from django.contrib.postgres.indexes import BrinIndex
from django.db import models
from django.utils import timezone
import uuid


class SoftDeletableModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    restored_at = models.DateTimeField(null=True, blank=True)
    deleted_via_cascade_from = models.UUIDField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def restore(self):
        self.deleted_at = None
        self.restored_at = timezone.now()
        self.deleted_via_cascade_from = None
        self.save(update_fields=['deleted_at', 'restored_at', 'deleted_via_cascade_from'])


class AuditAction(models.TextChoices):
    CREATE = 'CREATE', 'Create'
    UPDATE = 'UPDATE', 'Update'
    DELETE = 'DELETE', 'Delete'
    OVERRIDE = 'OVERRIDE', 'Override'
    LOCK = 'LOCK', 'Lock'
    UNLOCK = 'UNLOCK', 'Unlock'
    RUN = 'RUN', 'Run'
    LOGIN = 'LOGIN', 'Login'
    DISBURSE = 'DISBURSE', 'Disburse'
    GRADE = 'GRADE', 'Grade'
    PDF_GENERATED = 'PDF_GENERATED', 'PDF Generated'
    NOTIFY = 'NOTIFY', 'Notify'
    MEMBERSHIP_ADDED = 'MEMBERSHIP_ADDED', 'Membership Added'
    MEMBERSHIP_UPDATED = 'MEMBERSHIP_UPDATED', 'Membership Updated'
    MEMBERSHIP_DEACTIVATED = 'MEMBERSHIP_DEACTIVATED', 'Membership Deactivated'
    MEMBERSHIP_REACTIVATED = 'MEMBERSHIP_REACTIVATED', 'Membership Reactivated'
    ADMIN_CREATE = 'ADMIN_CREATE', 'Admin Create'
    ADMIN_UPDATE = 'ADMIN_UPDATE', 'Admin Update'
    ADMIN_DELETE = 'ADMIN_DELETE', 'Admin Delete'
    ADMIN_ACTION = 'ADMIN_ACTION', 'Admin Action'
    IMPERSONATE = 'IMPERSONATE', 'Impersonate'
    FORCE_STATUS = 'FORCE_STATUS', 'Force Status'
    TRANSFER_COOPERATIVE = 'TRANSFER_COOPERATIVE', 'Transfer Cooperative'
    ADMIN_PURGE = 'ADMIN_PURGE', 'Admin Purge'
    SNAPSHOT_FAILED = 'SNAPSHOT_FAILED', 'Snapshot Failed'
    EXPORT_FAILED = 'EXPORT_FAILED', 'Export Failed'
    PUBLISH = 'PUBLISH', 'Published legal document'
    ACCEPT = 'ACCEPT', 'Accepted legal document'
    DEACTIVATE = 'DEACTIVATE', 'Deactivated legal document'


class LocationMixin(models.Model):
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        abstract = True


class TenantQuerySet(models.QuerySet):
    def for_cooperative(self, cooperative_id):
        return self.filter(cooperative_id=cooperative_id)


class TenantManager(models.Manager):
    def get_queryset(self):
        qs = TenantQuerySet(self.model, using=self._db)
        if hasattr(self.model, 'deleted_at'):
            qs = qs.filter(deleted_at__isnull=True)
        return qs

    def all_with_trashed(self):
        qs = TenantQuerySet(self.model, using=self._db)
        if hasattr(self.model, 'deleted_at'):
            return qs
        return qs

    def trashed_only(self):
        qs = TenantQuerySet(self.model, using=self._db)
        if hasattr(self.model, 'deleted_at'):
            return qs.filter(deleted_at__isnull=False)
        return qs.none()

    def for_cooperative(self, cooperative_id):
        return self.get_queryset().for_cooperative(cooperative_id)


class CooperativeScopedModel(models.Model):
    cooperative = models.ForeignKey(
        'cooperatives.Cooperative',
        on_delete=models.CASCADE,
        related_name='%(class)s_set',
    )
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    restored_at = models.DateTimeField(null=True, blank=True)
    deleted_via_cascade_from = models.UUIDField(null=True, blank=True)

    objects = TenantManager()

    class Meta:
        abstract = True

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def restore(self):
        self.deleted_at = None
        self.restored_at = timezone.now()
        self.deleted_via_cascade_from = None
        self.save(update_fields=['deleted_at', 'restored_at', 'deleted_via_cascade_from'])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)


class AuditLog(CooperativeScopedModel):
    cooperative = models.ForeignKey(
        'cooperatives.Cooperative',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='audit_logs',
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, db_index=True
    )
    resource_type = models.CharField(max_length=100)
    resource_id = models.UUIDField(null=True, blank=True)
    action = models.CharField(
        max_length=50,
        choices=AuditAction.choices,
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    previous_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def changes(self):
        if self.previous_value is None and self.new_value is None:
            return None
        return {'previous': self.previous_value, 'new': self.new_value}

    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-created_at']
        default_permissions = ('view',)
        indexes = [
            BrinIndex(fields=['created_at']),
            models.Index(fields=['cooperative', 'resource_type', 'resource_id', 'created_at']),
            models.Index(fields=['cooperative', 'action', 'created_at'], name='idx_auditlog_coop_action_date'),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("AuditLog records cannot be updated")
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.actor} {self.action} {self.resource_type}:{self.resource_id} @ {self.created_at}'
