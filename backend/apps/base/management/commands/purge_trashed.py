from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cooperatives.models import Cooperative

User = get_user_model()


class Command(BaseCommand):
    help = 'Permanently deletes records that have been soft-deleted past the retention period'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int,
            default=settings.TRASH_RETENTION_DAYS,
            help=f'Retention period in days (default: {settings.TRASH_RETENTION_DAYS})',
        )
        parser.add_argument(
            '--execute', action='store_true',
            help='Actually purge. Without this flag it runs in dry-run mode.',
        )

    def handle(self, *args, **options):
        days = options['days']
        execute = options['execute']
        cutoff = timezone.now() - timedelta(days=days)

        self.stdout.write(f'Purging records soft-deleted before {cutoff.isoformat()}')
        if not execute:
            self.stdout.write('DRY RUN — use --execute to actually purge')

        models = [
            ('User', User),
            ('Cooperative', Cooperative),
        ]

        total = 0
        for label, model in models:
            qs = model.objects.all_with_trashed().filter(deleted_at__lt=cutoff)
            count = qs.count()
            if count:
                self.stdout.write(f'  {label}: {count} to purge')
                if execute:
                    for obj in qs:
                        obj.hard_delete()
                    self.stdout.write(f'    -> Purged {count} {label}(s)')
                total += count
            else:
                self.stdout.write(f'  {label}: none to purge')

        if execute:
            self.stdout.write(self.style.SUCCESS(f'Purge complete. {total} record(s) permanently deleted.'))
        else:
            self.stdout.write(self.style.WARNING(f'Dry run. {total} record(s) would be purged. Use --execute to proceed.'))
