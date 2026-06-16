import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.base.models import CooperativeScopedModel


class NotificationChannel(models.TextChoices):
    SMS = 'SMS', 'SMS'
    USSD = 'USSD', 'USSD'
    EMAIL = 'EMAIL', 'Email'
    IN_APP = 'IN_APP', 'In App'


class NotificationType(models.TextChoices):
    DELIVERY_CONFIRMATION = 'DELIVERY_CONFIRMATION', 'Delivery Confirmation'
    PAYMENT_SENT = 'PAYMENT_SENT', 'Payment Sent'
    PAYMENT_FAILED = 'PAYMENT_FAILED', 'Payment Failed'
    GRADE_RESULT = 'GRADE_RESULT', 'Grade Result'
    LOAN_APPROVAL = 'LOAN_APPROVAL', 'Loan Approval'
    LOAN_DISBURSEMENT = 'LOAN_DISBURSEMENT', 'Loan Disbursement'
    LOAN_DEFAULTED = 'LOAN_DEFAULTED', 'Loan Defaulted'
    USSD_SESSION = 'USSD_SESSION', 'USSD Session'
    GENERAL = 'GENERAL', 'General'


class NotificationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    SENT = 'SENT', 'Sent'
    FAILED = 'FAILED', 'Failed'


class Notification(CooperativeScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cooperative = models.ForeignKey(
        'cooperatives.Cooperative', on_delete=models.CASCADE,
        null=True, blank=True, related_name='notifications',
    )
    recipient = models.ForeignKey(
        'farmers.Farmer', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='notifications',
    )
    channel = models.CharField(max_length=10, choices=NotificationChannel.choices)
    notification_type = models.CharField(
        max_length=30, choices=NotificationType.choices, default=NotificationType.GENERAL,
    )
    content = models.TextField()
    status = models.CharField(
        max_length=10, choices=NotificationStatus.choices, default=NotificationStatus.PENDING, db_index=True,
    )
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    external_id = models.CharField(max_length=100, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cooperative', 'status', 'channel'], name='idx_notif_coop_status_chan'),
            models.Index(fields=['cooperative', 'channel'], condition=models.Q(status='PENDING'), name='idx_notification_unsent'),
        ]

    def __str__(self):
        return f'[{self.channel}] {self.notification_type} — {self.status}'

    def clean(self):
        if self.recipient and self.recipient.cooperative_id:
            if self.cooperative_id and self.cooperative_id != self.recipient.cooperative_id:
                raise ValidationError(
                    'Notification cooperative must match recipient farmer\'s cooperative.'
                )


class USSDSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.CharField(max_length=100, unique=True, db_index=True)
    phone_number = models.CharField(max_length=30)
    farmer = models.ForeignKey(
        'farmers.Farmer', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ussd_sessions',
    )
    membership = models.ForeignKey(
        'farmers.FarmerCooperativeMembership', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ussd_sessions',
    )
    current_menu = models.CharField(max_length=20, default='HOME')
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'USSD Session'
        verbose_name_plural = 'USSD Sessions'
        ordering = ['-last_activity']

    def __str__(self):
        return f'{self.session_id} — {self.phone_number} ({self.current_menu})'
