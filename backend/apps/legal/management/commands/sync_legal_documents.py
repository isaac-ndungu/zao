"""Sync legal documents from the tracked fixtures/ Markdown files.

Two modes:

* ``--mode seed``    — for first install only. Uses ``update_or_create``
  with ``version=1`` so re-running is a no-op on a clean environment.
  Re-running on an environment that already has the v1 row will OVERWRITE
  the v1 content in place. Re-running on an environment that already has
  a different active version will raise ``IntegrityError`` from the
  partial ``UniqueConstraint`` on ``(slug, is_active=True)``; that's
  expected and is the correct behavior.

* ``--mode publish`` — for subsequent updates. Reads the fixture files
  and creates a new versioned row, deactivating any prior active version
  atomically. This is the only safe way to update legal content after
  first install. The audit log records the publish with ``actor=None``
  (system action) so it is distinguishable from admin-driven publishes.

The two legacy commands (``seed_legal_documents`` and
``load_legal_documents``) are preserved as deprecation shims that
forward to this command.
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone


FIXTURES_DIR = settings.BASE_DIR / 'apps' / 'legal' / 'fixtures'

DOCUMENTS = [
    {
        'slug': 'privacy-policy',
        'title': 'Privacy Policy',
        'file': 'privacy-policy.md',
        'requires_acceptance': True,
    },
    {
        'slug': 'terms-of-service',
        'title': 'Terms and Conditions',
        'file': 'terms-of-service.md',
        'requires_acceptance': True,
    },
]


class Command(BaseCommand):
    help = (
        'Sync legal documents from fixtures/. '
        'Use --mode=seed for first install (idempotent v1 upsert), '
        'or --mode=publish for subsequent updates (creates a new version).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            choices=['seed', 'publish'],
            default='publish',
            help='seed = first install (v1 upsert); publish = create new version (default).',
        )

    def handle(self, *args, **options):
        from apps.legal.models import LegalDocument

        mode = options['mode']
        now = timezone.now()

        for spec in DOCUMENTS:
            filepath = FIXTURES_DIR / spec['file']
            if not filepath.exists():
                self.stdout.write(self.style.WARNING(
                    f'Fixture not found: {filepath} — skipping {spec["slug"]}'
                ))
                continue

            with open(filepath, encoding='utf-8') as f:
                content = f.read()

            if mode == 'seed':
                doc, created = LegalDocument.objects.update_or_create(
                    slug=spec['slug'],
                    defaults={
                        'title': spec['title'],
                        'content': content,
                        'version': 1,
                        'is_active': True,
                        'requires_acceptance': spec['requires_acceptance'],
                        'published_at': now,
                    },
                )
                verb = 'created' if created else 'updated'
                self.stdout.write(self.style.SUCCESS(
                    f'  [{mode}] {verb}: {doc.slug} v{doc.version} — "{doc.title}"'
                ))
            else:
                latest = (LegalDocument.objects
                          .filter(slug=spec['slug'])
                          .order_by('-version')
                          .first())
                new_version = (latest.version + 1) if latest else 1
                doc = LegalDocument.objects.publish_new(
                    slug=spec['slug'],
                    actor=None,
                    ip_address=None,
                    title=spec['title'],
                    content=content,
                    version=new_version,
                    requires_acceptance=spec['requires_acceptance'],
                    published_at=now,
                )
                self.stdout.write(self.style.SUCCESS(
                    f'  [{mode}] published: {doc.slug} v{doc.version} — "{doc.title}"'
                ))

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Processed {len(DOCUMENTS)} document(s) in --mode={mode}.'
        ))
