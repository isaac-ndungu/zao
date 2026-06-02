from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0006_add_audit_log_indexes'),
    ]

    operations = [
        TrigramExtension(),
    ]
