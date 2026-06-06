from django.db import migrations, models


def backfill_memberships(apps, schema_editor):
    Farmer = apps.get_model('farmers', 'Farmer')
    Membership = apps.get_model('farmers', 'FarmerCooperativeMembership')
    db_alias = schema_editor.connection.alias

    count = 0
    for farmer in Farmer.objects.using(db_alias).iterator():
        Membership.objects.using(db_alias).create(
            farmer=farmer,
            cooperative_id=farmer.cooperative_id,
            member_number=farmer.member_number or f'LEGACY-{farmer.id}',
            payment_method=farmer.payment_method or 'M-PESA',
            mpesa_number=farmer.mpesa_number or farmer.phone_number,
            bank_name=farmer.bank_name or '',
            bank_account=farmer.bank_account or '',
            bank_branch=farmer.bank_branch or '',
            is_active=True,
        )
        count += 1

    total = Farmer.objects.using(db_alias).count()
    memberships = Membership.objects.using(db_alias).count()
    assert memberships == total, (
        f'Backfill mismatch: {memberships} memberships created for {total} farmers'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('farmers', '0008_alter_farmer_bank_account_alter_farmer_bank_branch_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_memberships, reverse_code=migrations.RunPython.noop),
    ]
