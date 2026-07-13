import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cooperatives', '0001_initial'),
        ('grading', '0009_grade_payment_cycle'),
    ]

    operations = [
        migrations.AddField(
            model_name='gradeprice',
            name='cooperative',
            field=models.ForeignKey(
                blank=True,
                help_text='Null = global default price. Set for cooperative-specific pricing.',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='grade_prices',
                to='cooperatives.cooperative',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='gradeprice',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='gradeprice',
            constraint=models.UniqueConstraint(
                condition=models.Q(('cooperative__isnull', True)),
                fields=('grade_letter', 'effective_from'),
                name='uniq_global_grade_price',
            ),
        ),
        migrations.AddConstraint(
            model_name='gradeprice',
            constraint=models.UniqueConstraint(
                fields=('cooperative', 'grade_letter', 'effective_from'),
                name='uniq_coop_grade_price',
            ),
        ),
    ]
