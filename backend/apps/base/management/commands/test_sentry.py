import sys

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Verify Sentry integration is working'

    def handle(self, *args, **options):
        dsn = getattr(settings, 'SENTRY_DSN', '')
        if not dsn:
            self.stderr.write(self.style.ERROR(
                'SENTRY_DSN is not set. Add it to your .env and restart.'
            ))
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS(f'SENTRY_DSN is configured ({dsn[:20]}...)'))

        import sentry_sdk
        sentry_sdk.capture_message('Sentry integration test — Zao API')
        self.stdout.write(self.style.SUCCESS('Sent test message to Sentry. Check your dashboard.'))

        try:
            1 / 0
        except ZeroDivisionError:
            sentry_sdk.capture_exception()
            self.stdout.write(self.style.SUCCESS('Sent test exception to Sentry. Check your dashboard.'))

        self.stdout.write(self.style.SUCCESS('Done. If you see both events in Sentry, the integration is working.'))
