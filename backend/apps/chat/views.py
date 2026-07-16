import uuid

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

from .models import ChatMessage
from .serializers import ChatMessageSerializer, ChatRequestSerializer, ChatResponseSerializer
from .utils import ask_gemini
from .context import build_context_string
from .models import get_active_system_prompt

from apps.base.idempotency import idempotent
from .throttles import ChatRateThrottle


class ChatView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ChatRateThrottle]

    def get(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({'detail': 'session_id query parameter required.'}, status=400)
        messages = ChatMessage.objects.filter(session_id=session_id)
        serializer = ChatMessageSerializer(messages, many=True)
        return Response({'messages': serializer.data})

    @idempotent()
    def post(self, request):
        req_serializer = ChatRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)

        message = req_serializer.validated_data['message']
        session_id = req_serializer.validated_data.get('session_id', str(uuid.uuid4()))

        ChatMessage.objects.create(session_id=session_id, role='user', content=message)

        history = ChatMessage.objects.filter(session_id=session_id).values_list('role', 'content')
        system_prompt = get_active_system_prompt()
        messages = [{'role': 'system', 'content': system_prompt}]
        try:
            context = build_context_string()
            messages.append({'role': 'system', 'content': context})
        except Exception:
            pass
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
