"""Enforce 'one active version per slug' invariant.

Adds a partial UniqueConstraint on (slug) WHERE is_active=True so the
database itself rejects any attempt to have two active versions of the
same legal document. A data-cleanup step runs first to deactivate all
but the latest version of any slug that already has duplicates (which
is the exact state this migration is meant to fix).

The tie-breaker is deterministic: the row with the highest ``version``
wins; on a version tie, the row with the highest ``id`` (most recently
inserted) wins.
"""

from django.db import migrations, models


def cleanup_duplicate_active_slugs(apps, schema_editor):
    LegalDocument = apps.get_model('legal', 'LegalDocument')
    for slug in (LegalDocument.objects
                 .values_list('slug', flat=True).distinct()):
        keeper_pk = (LegalDocument.objects
                     .filter(slug=slug, is_active=True)
                     .order_by('-version', '-id')
                     .values_list('id', flat=True)
                     .first())
        if keeper_pk is None:
            continue
        (LegalDocument.objects
         .filter(slug=slug, is_active=True)
         .exclude(pk=keeper_pk)
         .update(is_active=False))


def reverse_noop(apps, schema_editor):
    """No reverse: removing the constraint leaves any historical duplicates
    in place. Manual cleanup would be required.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('legal', '0002_alter_legaldocument_slug'),
    ]

    operations = [
        migrations.RunPython(
            cleanup_duplicate_active_slugs,
            reverse_code=reverse_noop,
        ),
        migrations.AddConstraint(
            model_name='legaldocument',
            constraint=models.UniqueConstraint(
                fields=['slug'],
                condition=models.Q(is_active=True),
                name='uniq_active_slug',
            ),
        ),
    ]
