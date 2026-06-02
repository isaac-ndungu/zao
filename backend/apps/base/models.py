from django.contrib.auth import get_user_model
from django.contrib.postgres.indexes import BrinIndex
from django.db import models
import uuid


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
        return TenantQuerySet(self.model, using=self._db)

    def for_cooperative(self, cooperative_id):
        return self.get_queryset().for_cooperative(cooperative_id)


class CooperativeScopedModel(models.Model):
    cooperative = models.ForeignKey(
        'cooperatives.Cooperative',
        on_delete=models.CASCADE,
        related_name='%(class)s_set',
    )

    objects = TenantManager()

    class Meta:
        abstract = True


class AuditLog(CooperativeScopedModel):
    cooperative = models.ForeignKey(
        'cooperatives.Cooperative',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='audit_logs',
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True, blank=True
    )
    resource_type = models.CharField(max_length=100)
    resource_id = models.UUIDField()
    action = models.CharField(
        max_length=20,
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
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("AuditLog records cannot be updated")
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.actor} {self.action} {self.resource_type}:{self.resource_id} @ {self.created_at}'
