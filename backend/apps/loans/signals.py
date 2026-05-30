from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Loan


def _update_farmer_has_active_loan(loan):
    has_active = Loan.objects.filter(
        farmer=loan.farmer,
        status='ACTIVE',
        installments_paid__lt=models.F('number_of_installments'),
    ).exists()
    Farmer.objects.filter(id=loan.farmer_id).update(
        has_active_loan=has_active
    )


@receiver([post_save, post_delete], sender=Loan)
def update_has_active_loan(sender, instance, **kwargs):
    from django.db import models
    from apps.farmers.models import Farmer
    has_active = Loan.objects.filter(
        farmer=instance.farmer,
        status='ACTIVE',
        installments_paid__lt=models.F('number_of_installments'),
    ).exists()
    Farmer.objects.filter(id=instance.farmer_id).update(
        has_active_loan=has_active
    )
