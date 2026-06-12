from django.forms.models import model_to_dict

from apps.base.models import AuditAction
from apps.base.throttles import SuperAdminThrottle
from apps.base.utils import log_audit
from apps.admin.permissions import IsSuperUser


class ModelAdminMixin:
    permission_classes = [IsSuperUser]
    throttle_classes = [SuperAdminThrottle]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type=instance._meta.model_name,
            resource_id=instance.pk,
            action=AuditAction.ADMIN_CREATE,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )

    def perform_update(self, serializer):
        old = model_to_dict(serializer.instance)
        instance = serializer.save()
        log_audit(
            actor=self.request.user,
            resource_type=instance._meta.model_name,
            resource_id=instance.pk,
            action=AuditAction.ADMIN_UPDATE,
            previous_value=old,
            new_value=model_to_dict(instance),
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )

    def perform_destroy(self, instance):
        log_audit(
            actor=self.request.user,
            resource_type=instance._meta.model_name,
            resource_id=instance.pk,
            action=AuditAction.ADMIN_DELETE,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )
        instance.delete()
