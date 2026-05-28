from apps.base.models import AuditLog


def log_audit(actor, resource_type, resource_id, action, previous_value=None, new_value=None, cooperative_id=None):
    if not cooperative_id and actor:
        cooperative_id = getattr(actor, 'cooperative_id', None)
    return AuditLog.objects.create(
        actor=actor,
        cooperative_id=cooperative_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        previous_value=previous_value,
        new_value=new_value,
    )
