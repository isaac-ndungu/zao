import uuid

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

from .models import ChatMessage
from .serializers import ChatMessageSerializer, ChatRequestSerializer, ChatResponseSerializer
from .utils import ask_gemini

SYSTEM_PROMPT = (
    'You are a helpful assistant for the Zao Agricultural Cooperative Management API. '
    'Answer questions about how to use the API, what endpoints exist, and how they work.\n\n'
    'Be concise, accurate, and include example endpoints where helpful.\n\n'
    'Here is the API description:\n\n' + settings.SPECTACULAR_SETTINGS['DESCRIPTION']
)


class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({'detail': 'session_id query parameter required.'}, status=400)
        messages = ChatMessage.objects.filter(session_id=session_id)
        serializer = ChatMessageSerializer(messages, many=True)
        return Response({'messages': serializer.data})

    def post(self, request):
        req_serializer = ChatRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)

        message = req_serializer.validated_data['message']
        session_id = req_serializer.validated_data.get('session_id', str(uuid.uuid4()))

        ChatMessage.objects.create(session_id=session_id, role='user', content=message)

        history = ChatMessage.objects.filter(session_id=session_id).values_list('role', 'content')
        messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
        for role, content in history:
            messages.append({'role': role, 'content': content})

        try:
            reply = ask_gemini(messages)
        except Exception as e:
            return Response({'detail': f'AI service error: {e}'}, status=502)

        ChatMessage.objects.create(session_id=session_id, role='assistant', content=reply)

        res_serializer = ChatResponseSerializer(data={'reply': reply, 'session_id': session_id})
        res_serializer.is_valid()
        return Response(res_serializer.data, status=status.HTTP_200_OK)
