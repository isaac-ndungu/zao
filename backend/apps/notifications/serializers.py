from rest_framework import serializers

from .models import ContactMessage, Notification


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'subject', 'message']
        read_only_fields = ['id']

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError('Name must be at least 2 characters.')
        return value

    def validate_subject(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError('Subject must be at least 2 characters.')
        return value

    def validate_message(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError('Message must be at least 10 characters.')
        return value


class ContactMessageAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'subject', 'message', 'is_read', 'created_at']
        read_only_fields = ['id', 'name', 'email', 'subject', 'message', 'created_at']


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
