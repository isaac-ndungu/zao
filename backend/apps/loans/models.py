import uuid
from django.db import models

from apps.base.models import CooperativeScopedModel


class LoanStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Approval'
    ACTIVE = 'ACTIVE', 'Active'
    COMPLETED = 'COMPLETED', 'Completed'
    DEFAULTED = 'DEFAULTED', 'Defaulted'


class GuarantorStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    RELEASED = 'RELEASED', 'Released'


class Loan(CooperativeScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(
        'farmers.Farmer', on_delete=models.PROTECT,
        related_name='loans',
    )
    amount_principal = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    total_repayable = models.DecimalField(max_digits=12, decimal_places=2)
    installment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    number_of_installments = models.PositiveIntegerField()
    installments_paid = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=LoanStatus.choices, default=LoanStatus.PENDING, db_index=True,
    )
    approved_by = models.ForeignKey(
        'auth_api.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_loans',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    disbursed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Loan'
        verbose_name_plural = 'Loans'
        ordering = ['-created_at']

    def __str__(self):
        mn = self.farmer.primary_membership.member_number if self.farmer.primary_membership else '---'
        return f'Loan {self.id} — {mn}'

    def save(self, *args, **kwargs):
        if not self.total_repayable or not self.installment_amount:
            rate = float(self.interest_rate) / 100
            self.total_repayable = round(
                float(self.amount_principal) * (1 + rate), 2
            )
            self.installment_amount = round(
                float(self.total_repayable) / self.number_of_installments, 2
            )
        super().save(*args, **kwargs)


class LoanRepayment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan = models.ForeignKey(
        Loan, on_delete=models.CASCADE, related_name='repayments',
    )
    farmer_payment = models.ForeignKey(
        'payment_engine.FarmerPayment', on_delete=models.CASCADE,
        related_name='loan_repayments',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Loan Repayment'
        verbose_name_plural = 'Loan Repayments'
        unique_together = ('loan', 'farmer_payment')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.loan} — {self.amount}'


class LoanGuarantor(CooperativeScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    loan = models.ForeignKey(
        Loan, on_delete=models.CASCADE, related_name='guarantors',
    )
    guarantor = models.ForeignKey(
        'farmers.Farmer', on_delete=models.PROTECT,
        related_name='guaranteed_loans',
    )
    agreed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=GuarantorStatus.choices, default=GuarantorStatus.ACTIVE,
    )

    class Meta:
        verbose_name = 'Loan Guarantor'
        verbose_name_plural = 'Loan Guarantors'
        unique_together = ('loan', 'guarantor')

    def __str__(self):
        mn = self.guarantor.primary_membership.member_number if self.guarantor.primary_membership else '---'
        return f'{mn} → {self.loan} [{self.status}]'
