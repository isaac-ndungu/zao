from rest_framework import serializers

from .models import Notification


class NotificationListSerializer(serializers.ModelSerializer):
    recipient_name = serializers.SerializerMethodField()
    recipient_phone = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'channel', 'notification_type', 'content',
            'status', 'retry_count', 'external_id', 'cost',
            'recipient', 'recipient_name', 'recipient_phone',
            'sent_at', 'created_at',
        ]

    def get_recipient_name(self, obj):
        if obj.recipient:
            return f'{obj.recipient.first_name} {obj.recipient.last_name}'
        return None

    def get_recipient_phone(self, obj):
        if obj.recipient:
            return obj.recipient.phone_number
        return None


class NotificationDetailSerializer(serializers.ModelSerializer):
    recipient_name = serializers.SerializerMethodField()
    recipient_phone = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = '__all__'

    def get_recipient_name(self, obj):
        if obj.recipient:
            return f'{obj.recipient.first_name} {obj.recipient.last_name}'
        return None

    def get_recipient_phone(self, obj):
        if obj.recipient:
            return obj.recipient.phone_number
        return None
