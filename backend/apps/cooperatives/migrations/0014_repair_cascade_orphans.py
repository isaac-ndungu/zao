import logging

from django.db import migrations
from django.utils import timezone

logger = logging.getLogger(__name__)


def repair_orphaned_cascade_records(apps, schema_editor):
    Cooperative = apps.get_model('cooperatives', 'Cooperative')
    deleted_coop_ids = list(
        Cooperative.objects.filter(deleted_at__isnull=False).values_list('pk', flat=True)
    )
    if not deleted_coop_ids:
        return

    from apps.base.models import CooperativeScopedModel

    now = timezone.now()
    total_repaired = 0

    for model_cls, fk_field in CooperativeScopedModel._registry:
        if model_cls._meta.abstract:
            continue
        try:
            model = apps.get_model(model_cls._meta.app_label, model_cls.__name__)
        except LookupError:
            continue
        if not hasattr(model, 'deleted_at'):
            continue

        for coop_id in deleted_coop_ids:
            updated = model.objects.filter(
                **{fk_field: coop_id},
                deleted_at__isnull=True,
            ).update(
                deleted_at=now,
                deleted_via_cascade_from=coop_id,
            )
            total_repaired += updated

    if total_repaired > 0:
        logger.info('Repaired %d orphaned cascade records', total_repaired)


def reverse_repair(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cooperatives', '0013_remove_cooperative_coffee_levy_per_kg_and_more'),
        ('base', '0013_add_performance_indexes'),
    ]

    operations = [
        migrations.RunPython(repair_orphaned_cascade_records, reverse_repair),
    ]
