import uuid

from django.conf import settings
from django.core.cache import cache
from django.db import models, transaction

CHATBOT_PROMPT_CACHE_KEY = 'chatbot:active_system_prompt'
CHATBOT_PROMPT_CACHE_TTL = 3600


def get_active_system_prompt():
    prompt = cache.get(CHATBOT_PROMPT_CACHE_KEY)
    if prompt is not None:
        return prompt
    config = ChatbotConfig.objects.filter(is_active=True).first()
    if config is None:
        import logging
        logging.getLogger(__name__).error(
            'No active ChatbotConfig found — chatbot running without system prompt'
        )
        prompt = (
            'You are a helpful assistant for the Zao Agricultural Cooperative '
            'Management Platform. I currently have limited configuration. '
            'Please ask specific questions about the API.'
        )
    else:
        prompt = config.system_prompt
    cache.set(CHATBOT_PROMPT_CACHE_KEY, prompt, timeout=CHATBOT_PROMPT_CACHE_TTL)
    return prompt


class ChatbotConfigManager(models.Manager):
    def publish_new(self, prompt_text, user):
        with transaction.atomic():
            last = ChatbotConfig.objects.order_by('-version').first()
            next_version = (last.version + 1) if last else 1
            ChatbotConfig.objects.filter(is_active=True).update(is_active=False)
            new_config = ChatbotConfig.objects.create(
                system_prompt=prompt_text,
                version=next_version,
                is_active=True,
                created_by=user,
            )
        cache.delete(CHATBOT_PROMPT_CACHE_KEY)
        return new_config


class ChatbotConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    system_prompt = models.TextField()
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )

    objects = ChatbotConfigManager()

    class Meta:
        ordering = ['-version']
        constraints = [
            models.UniqueConstraint(
                fields=['is_active'],
                condition=models.Q(is_active=True),
                name='uniq_active_chatbot_config',
            ),
        ]

    def __str__(self):
        status = 'active' if self.is_active else 'inactive'
        return f'ChatbotConfig v{self.version} ({status})'


class ChatMessage(models.Model):
    session_id = models.UUIDField(db_index=True)
    role = models.CharField(max_length=20, choices=[('user', 'User'), ('assistant', 'Assistant')])
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
