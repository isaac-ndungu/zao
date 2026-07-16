import logging

from django.core.management.base import BaseCommand

from apps.base.models import CooperativeScopedModel
from apps.cooperatives.models import Cooperative

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'Find orphaned related records that should have been cascade '
        'soft-deleted when their parent cooperative was soft-deleted.'
    )

    def handle(self, *args, **options):
        deleted_coop_ids = set(
            Cooperative.objects.all_with_trashed()
            .filter(deleted_at__isnull=False)
            .values_list('pk', flat=True)
        )
        if not deleted_coop_ids:
            self.stdout.write(self.style.SUCCESS('No soft-deleted cooperatives found. Nothing to check.'))
            return

        self.stdout.write(
            f'Checking {len(deleted_coop_ids)} soft-deleted cooperatives '
            f'across {len(CooperativeScopedModel._registry)} registered models...\n'
        )

        total_orphans = 0
        for model_cls, fk_field in CooperativeScopedModel._registry:
            qs = model_cls.objects.all_with_trashed() if hasattr(model_cls.objects, 'all_with_trashed') else model_cls.objects
            orphans = qs.filter(
                **{f'{fk_field}__in': deleted_coop_ids},
                deleted_at__isnull=True,
            )
            count = orphans.count()
            if count > 0:
                total_orphans += count
                self.stdout.write(self.style.WARNING(
                    f'  {model_cls.__name__}: {count} orphaned record(s)'
                ))
                for obj in orphans[:10]:
                    self.stdout.write(
                        f'    - pk={obj.pk} {fk_field}={getattr(obj, fk_field + "_id")}'
                    )
                if count > 10:
                    self.stdout.write(f'    ... and {count - 10} more')

        if total_orphans == 0:
            self.stdout.write(self.style.SUCCESS('No orphaned records found.'))
        else:
            self.stdout.write(self.style.WARNING(
                f'\nTotal: {total_orphans} orphaned record(s) across '
                f'{len(deleted_coop_ids)} soft-deleted cooperative(s).'
            ))
            self.stdout.write(
                'Run the data migration to repair these orphans after reviewing.'
            )
