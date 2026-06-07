from rest_framework import serializers

from .models import ChatMessage


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(help_text='User\'s question about the Zao API')
    session_id = serializers.CharField(required=False, help_text='Optional session UUID for conversation continuity')


class ChatResponseSerializer(serializers.Serializer):
    reply = serializers.CharField(help_text='Assistant response')
    session_id = serializers.CharField(help_text='Session UUID for conversation continuity')


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'created_at']
