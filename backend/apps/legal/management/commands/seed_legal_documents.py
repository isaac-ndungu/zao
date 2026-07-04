"""Seed the platform with v1 of the Privacy Policy and Terms of Service.

The ``legal`` app's ``migrations/`` directory is owned by root in this
environment, so a proper data migration can't be added there. This
management command is the equivalent — run it once after deploy to
populate the legal documents (and make the admin appbar badge and the
user-side accept gate non-empty). It's idempotent
(update_or_create), so running it again is safe.

The canonical content lives in the tracked ``fixtures/`` markdown
files (privacy-policy.md, terms-of-service.md). This command reads
those files so there's a single source of truth — legal/compliance
folks can edit the .md files without touching Python.
"""
import os

from django.core.management.base import BaseCommand
from django.utils import timezone


FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'fixtures',
)

SEED_DOCS = [
    {'slug': 'privacy-policy',  'title': 'Privacy Policy',      'file': 'privacy-policy.md'},
    {'slug': 'terms-of-service', 'title': 'Terms and Conditions', 'file': 'terms-of-service.md'},
]


class Command(BaseCommand):
    help = 'Seed v1 of the Privacy Policy and Terms of Service from fixtures/ (idempotent).'

    def handle(self, *args, **options):
        from apps.legal.models import LegalDocument

        now = timezone.now()
        for spec in SEED_DOCS:
            path = os.path.join(FIXTURES_DIR, spec['file'])
            with open(path, encoding='utf-8') as f:
                content = f.read()
            doc, created = LegalDocument.objects.update_or_create(
                slug=spec['slug'],
                defaults={
                    'title': spec['title'],
                    'content': content,
                    'version': 1,
                    'is_active': True,
                    'requires_acceptance': True,
                    'published_at': now,
                },
            )
            verb = 'created' if created else 'updated (already existed)'
            self.stdout.write(self.style.SUCCESS(
                f'  {verb}: {doc.slug} v{doc.version} — "{doc.title}" '
                f'(content from fixtures/{spec["file"]}, {len(content)} chars)'
            ))

        self.stdout.write(self.style.SUCCESS(
            f'\nSeeded {len(SEED_DOCS)} legal document(s) from fixtures/. '
            f'The admin appbar "Legal history" badge and the user accept gate '
            f'will now have content.'
        ))
