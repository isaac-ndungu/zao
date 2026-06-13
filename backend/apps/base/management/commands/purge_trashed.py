from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.base.constants import get_soft_deletable_models


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

        models = get_soft_deletable_models()

        total = 0
        for model_cls in models:
            mgr = model_cls.objects
            all_with_trashed = mgr.all_with_trashed if hasattr(mgr, 'all_with_trashed') else mgr
            qs = all_with_trashed().filter(deleted_at__lt=cutoff)
            count = qs.count()
            label = model_cls.__name__
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
