from django.conf import settings
from django.db import models
from django.utils import timezone
import uuid


class LegalDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(
        max_length=100, db_index=True,
        help_text='e.g. privacy-policy, terms-of-service',
    )
    title = models.CharField(max_length=255)
    content = models.TextField(help_text='Markdown content')
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=False)
    requires_acceptance = models.BooleanField(
        default=False,
        help_text='If True, users must accept the latest version before using the app',
    )
    published_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Null means draft. Only documents with published_at <= now() are visible.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Legal Document'
        verbose_name_plural = 'Legal Documents'
        ordering = ['-published_at', '-version']
        indexes = [
            models.Index(fields=['slug', 'is_active', 'published_at']),
        ]

    def __str__(self):
        return f'{self.slug} v{self.version}'


class LegalAcceptance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='legal_acceptances',
    )
    document = models.ForeignKey(
        LegalDocument, on_delete=models.PROTECT,
        related_name='acceptances',
    )
    version = models.PositiveIntegerField(
        help_text='Snapshot of the document version at acceptance time',
    )
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Legal Acceptance'
        verbose_name_plural = 'Legal Acceptances'
        unique_together = [['user', 'document', 'version']]
        indexes = [
            models.Index(fields=['user', 'document']),
        ]

    def __str__(self):
        return f'{self.user.email} accepted {self.document.slug} v{self.version}'
