from django.db import migrations, models


def set_empty_prefix_to_null(apps, schema_editor):
    Cooperative = apps.get_model('cooperatives', 'Cooperative')
    Cooperative.objects.filter(prefix='').update(prefix=None)


class Migration(migrations.Migration):

    dependencies = [
        ('cooperatives', '0010_cooperative_deleted_via_cascade_from'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cooperative',
            name='prefix',
            field=models.CharField(blank=True, max_length=10, null=True, unique=True),
        ),
        migrations.RunPython(set_empty_prefix_to_null, migrations.RunPython.noop),
    ]
