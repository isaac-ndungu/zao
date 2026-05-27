from django.contrib.auth import get_user_model
from django.db import models
import uuid


class CooperativeScopedModel(models.Model):
    cooperative = models.ForeignKey(
        'cooperatives.Cooperative',
        on_delete=models.CASCADE,
        related_name='%(class)s_set',
    )

    class Meta:
        abstract = True


class AuditLog(CooperativeScopedModel):
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
