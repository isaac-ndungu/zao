"""DEPRECATED: use ``sync_legal_documents --mode=seed`` instead.

This command is preserved as a deprecation shim so existing scripts
and cron entries do not break. It forwards to the unified command in
``seed`` mode (idempotent v1 upsert).
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'DEPRECATED. Use: python manage.py sync_legal_documents --mode=seed'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            'seed_legal_documents is deprecated. Use sync_legal_documents --mode=seed instead.'
        ))
        call_command('sync_legal_documents', '--mode=seed')
