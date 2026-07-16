from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.cache import cache
from rest_framework import status

from apps.chat.models import ChatMessage, ChatbotConfig, CHATBOT_PROMPT_CACHE_KEY

pytestmark = pytest.mark.django_db


# =============================================================================
# ChatbotConfig Model Tests
# =============================================================================

class TestChatbotConfig:
    def test_publish_new(self, api_client):
        config = ChatbotConfig.objects.publish_new('Test prompt v1', api_client.user)
        assert config.pk is not None
        assert config.version == 1
        assert config.is_active is True
        assert config.system_prompt == 'Test prompt v1'
        assert config.created_by == api_client.user

    def test_publish_new_deactivates_old(self, api_client):
        ChatbotConfig.objects.publish_new('Prompt v1', api_client.user)
        config2 = ChatbotConfig.objects.publish_new('Prompt v2', api_client.user)
        assert config2.is_active is True
        assert ChatbotConfig.objects.filter(is_active=True).count() == 1
        old = ChatbotConfig.objects.get(system_prompt='Prompt v1')
        assert old.is_active is False

    def test_publish_new_increments_version(self, api_client):
        c1 = ChatbotConfig.objects.publish_new('V1', api_client.user)
        c2 = ChatbotConfig.objects.publish_new('V2', api_client.user)
        assert c2.version == c1.version + 1

    def test_publish_new_clears_cache(self, api_client):
        cache.clear()
        cache.set(CHATBOT_PROMPT_CACHE_KEY, 'stale')
        ChatbotConfig.objects.publish_new('New prompt', api_client.user)
        assert cache.get(CHATBOT_PROMPT_CACHE_KEY) is None

    def test_str(self, api_client):
        config = ChatbotConfig.objects.publish_new('Prompt', api_client.user)
        assert 'v1' in str(config)
        assert 'active' in str(config)


class TestGetActiveSystemPrompt:
    def test_returns_active_config(self, api_client):
        ChatbotConfig.objects.publish_new('My prompt', api_client.user)
        from apps.chat.models import get_active_system_prompt
        assert get_active_system_prompt() == 'My prompt'

    def test_fallback_when_no_config(self, api_client):
        cache.clear()
        from apps.chat.models import get_active_system_prompt
        prompt = get_active_system_prompt()
        assert 'limited configuration' in prompt

    def test_uses_cache(self, api_client):
        cache.clear()
        cache.set(CHATBOT_PROMPT_CACHE_KEY, 'cached prompt')
        from apps.chat.models import get_active_system_prompt
        assert get_active_system_prompt() == 'cached prompt'


# =============================================================================
# Chat Model Tests
# =============================================================================

class TestChatMessage:
    def test_create(self):
        msg = ChatMessage.objects.create(
            session_id=uuid4(),
            role='user',
            content='Hello, how are you?',
        )
        assert msg.pk is not None
        assert msg.role == 'user'

    def test_assistant_message(self):
        msg = ChatMessage.objects.create(
            session_id=uuid4(),
            role='assistant',
            content='I am doing well!',
        )
        assert msg.role == 'assistant'

    def test_ordering(self):
        session_id = uuid4()
        m1 = ChatMessage.objects.create(session_id=session_id, role='user', content='First')
        m2 = ChatMessage.objects.create(session_id=session_id, role='assistant', content='Second')
        messages = list(ChatMessage.objects.filter(session_id=session_id))
        assert messages[0] == m1
        assert messages[1] == m2

    def test_session_id_indexed(self):
        sid = uuid4()
        ChatMessage.objects.create(session_id=sid, role='user', content='Test')
        assert ChatMessage.objects.filter(session_id=sid).count() == 1


# =============================================================================
# Chat API Endpoint Tests
# =============================================================================

class TestChatAPI:
    def test_get_messages_unauthenticated(self, client):
        resp = client.get(f'/api/chat/?session_id={uuid4()}')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_messages_no_session_id(self, api_client):
        resp = api_client.get('/api/chat/')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'session_id' in resp.json()['detail']

    def test_get_messages_empty(self, api_client):
        session_id = uuid4()
        resp = api_client.get(f'/api/chat/?session_id={session_id}')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['messages'] == []

    def test_get_messages_with_history(self, api_client):
        session_id = uuid4()
        ChatMessage.objects.create(session_id=session_id, role='user', content='Hi')
        ChatMessage.objects.create(session_id=session_id, role='assistant', content='Hello')
        resp = api_client.get(f'/api/chat/?session_id={session_id}')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()['messages']) == 2

    def test_post_unauthenticated(self, client):
        resp = client.post('/api/chat/', {'message': 'Hello'}, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @patch('apps.chat.views.ask_gemini')
    def test_post_message(self, mock_ask, api_client):
        mock_ask.return_value = 'Sure, I can help with that!'
        resp = api_client.post('/api/chat/', {'message': 'How do I create a loan?'}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert 'reply' in data
        assert 'session_id' in data
        assert data['reply'] == 'Sure, I can help with that!'
        mock_ask.assert_called_once()

    @patch('apps.chat.views.ask_gemini')
    def test_post_with_session_id(self, mock_ask, api_client):
        mock_ask.return_value = 'Response'
        session_id = str(uuid4())
        resp = api_client.post('/api/chat/', {
            'message': 'Hello',
            'session_id': session_id,
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['session_id'] == session_id

    @patch('apps.chat.views.ask_gemini')
    def test_post_stores_both_messages(self, mock_ask, api_client):
        mock_ask.return_value = 'Bot reply'
        session_id = str(uuid4())
        api_client.post('/api/chat/', {
            'message': 'User message',
            'session_id': session_id,
        }, format='json')
        messages = ChatMessage.objects.filter(session_id=session_id).order_by('created_at')
        assert messages.count() == 2
        assert messages[0].role == 'user'
        assert messages[0].content == 'User message'
        assert messages[1].role == 'assistant'
        assert messages[1].content == 'Bot reply'

    @patch('apps.chat.views.ask_gemini')
    def test_post_empty_message(self, mock_ask, api_client):
        resp = api_client.post('/api/chat/', {'message': ''}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @patch('apps.chat.views.ask_gemini', side_effect=Exception('AI down'))
    def test_post_ai_error(self, mock_ask, api_client):
        resp = api_client.post('/api/chat/', {'message': 'Hello'}, format='json')
        assert resp.status_code == status.HTTP_502_BAD_GATEWAY
        assert 'AI service error' in resp.json()['detail']
