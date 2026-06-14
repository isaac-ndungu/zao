import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_api', '0005_user_avatar'),
    ]

    operations = [
        migrations.CreateModel(
            name='BackupCode',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code_hash', models.CharField(max_length=128)),
                ('is_used', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='backup_codes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Backup Code',
                'verbose_name_plural': 'Backup Codes',
            },
        ),
    ]
