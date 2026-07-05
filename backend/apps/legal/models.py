from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
import uuid


class LegalDocumentManager(models.Manager):
    def publish_new(self, slug, *, actor=None, ip_address=None, **fields):
        """Atomically supersede any active version of ``slug`` and create a new one.

        Steps performed inside a single transaction:
        1. Mark all currently-active rows of this slug as ``is_active=False``.
        2. Insert the new row as ``is_active=True``.
        3. Write an audit log entry recording the publish event.

        Returns the newly-created :class:`LegalDocument`. The partial
        ``UniqueConstraint`` on ``(slug, is_active=True)`` guarantees that
        if the transaction ever commits with two active rows for the same
        slug, the database will reject the second insert.
        """
        from apps.base.models import AuditAction
        from apps.base.utils import log_audit

        with transaction.atomic():
            LegalDocument = self.model
            LegalDocument.objects.filter(slug=slug, is_active=True).update(
                is_active=False
            )
            new_doc = LegalDocument.objects.create(
                slug=slug, is_active=True, **fields
            )
            log_audit(
                actor=actor,
                resource_type='LegalDocument',
                resource_id=new_doc.pk,
                action=AuditAction.PUBLISH,
                new_value={
                    'slug': slug,
                    'version': new_doc.version,
                    'requires_acceptance': new_doc.requires_acceptance,
                },
                ip_address=ip_address,
            )
            return new_doc


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

    objects = LegalDocumentManager()

    class Meta:
        verbose_name = 'Legal Document'
        verbose_name_plural = 'Legal Documents'
        ordering = ['-published_at', '-version']
        indexes = [
            models.Index(fields=['slug', 'is_active', 'published_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['slug'],
                condition=models.Q(is_active=True),
                name='uniq_active_slug',
            ),
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
