from rest_framework import serializers

from apps.base.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    cooperative_name = serializers.SerializerMethodField()
    changes = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id', 'actor', 'actor_name', 'cooperative', 'cooperative_name',
            'resource_type', 'resource_id', 'action', 'changes',
            'ip_address', 'created_at',
        ]

    def get_actor_name(self, obj):
        if obj.actor:
            return f'{obj.actor.first_name} {obj.actor.last_name}'
        return None

    def get_cooperative_name(self, obj):
        if obj.cooperative:
            return obj.cooperative.name
        return None

    def get_changes(self, obj):
        return obj.changes
