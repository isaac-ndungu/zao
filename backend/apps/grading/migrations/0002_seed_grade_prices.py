from django.db import migrations


def seed_grade_prices(apps, schema_editor):
    GradePrice = apps.get_model('grading', 'GradePrice')
    GradePrice.objects.bulk_create([
        GradePrice(grade_letter='A', price_per_unit=50.00, effective_from='2026-01-01'),
        GradePrice(grade_letter='B', price_per_unit=45.00, effective_from='2026-01-01'),
        GradePrice(grade_letter='C', price_per_unit=38.00, effective_from='2026-01-01'),
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('grading', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_grade_prices),
    ]
