from apps.base.models import AuditLog


def log_audit(actor, resource_type, action, previous_value=None, new_value=None):
    return AuditLog.objects.create(
        actor=actor,
        resource_type=resource_type,
        action=action,
        previous_value=previous_value,
        new_value=new_value,
    )
