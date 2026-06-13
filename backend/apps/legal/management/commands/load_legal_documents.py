import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.legal.models import LegalDocument


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
    help = 'Load legal documents from Markdown fixture files'

    def handle(self, *args, **options):
        for doc in DOCUMENTS:
            filepath = os.path.join(FIXTURES_DIR, doc['file'])
            if not os.path.exists(filepath):
                self.stdout.write(self.style.WARNING(f'Fixture not found: {filepath} — skipping {doc["slug"]}'))
                continue

            with open(filepath) as f:
                content = f.read()

            existing = LegalDocument.objects.filter(slug=doc['slug']).order_by('-version').first()
            next_version = (existing.version + 1) if existing else 1

            LegalDocument.objects.create(
                slug=doc['slug'],
                title=doc['title'],
                content=content,
                version=next_version,
                is_active=True,
                requires_acceptance=doc['requires_acceptance'],
                published_at=timezone.now(),
            )
            self.stdout.write(self.style.SUCCESS(
                f'Loaded {doc["slug"]} v{next_version}'
            ))
