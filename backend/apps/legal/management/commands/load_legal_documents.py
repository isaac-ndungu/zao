"""DEPRECATED: use ``sync_legal_documents --mode=publish`` instead.

This command is preserved as a deprecation shim so existing scripts
and cron entries do not break. It forwards to the unified command in
``publish`` mode (creates a new version, supersedes prior active row).
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'DEPRECATED. Use: python manage.py sync_legal_documents --mode=publish'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            'load_legal_documents is deprecated. Use sync_legal_documents --mode=publish instead.'
        ))
        call_command('sync_legal_documents', '--mode=publish')
