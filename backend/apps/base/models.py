from django.contrib.auth import get_user_model
from django.db import models
import uuid


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
        choices=[
            ('CREATE', 'Create'),
            ('UPDATE', 'Update'),
            ('DELETE', 'Delete'),
            ('OVERRIDE', 'Override'),
            ('LOCK', 'Lock'),
            ('UNLOCK', 'Unlock'),
        ]
    )
    previous_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-created_at']
        default_permissions = ('view',)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("AuditLog records cannot be updated")
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.actor} {self.action} {self.resource_type}:{self.resource_id} @ {self.created_at}'
