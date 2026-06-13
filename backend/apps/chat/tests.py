import uuid

import pytest

from apps.chat.models import ChatMessage

pytestmark = pytest.mark.django_db


class TestChatMessage:
    def test_create(self):
        msg = ChatMessage.objects.create(
            session_id=uuid.uuid4(),
            role='user',
            content='Hello, how are you?',
        )
        assert msg.pk is not None
        assert msg.role == 'user'

    def test_assistant_message(self):
        msg = ChatMessage.objects.create(
            session_id=uuid.uuid4(),
            role='assistant',
            content='I am doing well!',
        )
        assert msg.role == 'assistant'

    def test_ordering(self):
        session_id = uuid.uuid4()
        m1 = ChatMessage.objects.create(session_id=session_id, role='user', content='First')
        m2 = ChatMessage.objects.create(session_id=session_id, role='assistant', content='Second')
        messages = list(ChatMessage.objects.filter(session_id=session_id))
        assert messages[0] == m1
        assert messages[1] == m2

    def test_session_id_indexed(self):
        sid = uuid.uuid4()
        ChatMessage.objects.create(session_id=sid, role='user', content='Test')
        assert ChatMessage.objects.filter(session_id=sid).count() == 1
