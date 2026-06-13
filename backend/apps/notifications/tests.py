import uuid
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

pytestmark = pytest.mark.django_db

from apps.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    USSDSession,
)


class TestNotificationModel:
    def test_create(self, cooperative, farmer):
        notif = Notification.objects.create(
            cooperative=cooperative,
            recipient=farmer,
            channel=NotificationChannel.SMS,
            notification_type=NotificationType.DELIVERY_CONFIRMATION,
            content='Your delivery has been received.',
        )
        assert notif.pk is not None
        assert notif.status == NotificationStatus.PENDING

    def test_str(self, cooperative):
        notif = Notification.objects.create(
            cooperative=cooperative,
            channel=NotificationChannel.SMS,
            notification_type=NotificationType.GENERAL,
            content='Test',
        )
        assert 'SMS' in str(notif)
        assert 'GENERAL' in str(notif)
        assert 'PENDING' in str(notif)

    def test_status_transitions(self, cooperative):
        notif = Notification.objects.create(
            cooperative=cooperative,
            channel=NotificationChannel.EMAIL,
            notification_type=NotificationType.PAYMENT_SENT,
            content='Payment sent',
        )
        notif.status = NotificationStatus.SENT
        notif.save()
        notif.refresh_from_db()
        assert notif.status == NotificationStatus.SENT

    def test_failed_status(self, cooperative):
        notif = Notification.objects.create(
            cooperative=cooperative,
            channel=NotificationChannel.SMS,
            notification_type=NotificationType.PAYMENT_FAILED,
            content='Payment failed',
            status=NotificationStatus.FAILED,
            error_message='Network error',
        )
        assert notif.status == NotificationStatus.FAILED
        assert 'Network error' in notif.error_message

    def test_retry_count(self, cooperative):
        notif = Notification.objects.create(
            cooperative=cooperative,
            channel=NotificationChannel.SMS,
            notification_type=NotificationType.GENERAL,
            content='Retry test',
        )
        assert notif.retry_count == 0
        assert notif.max_retries == 3

    def test_cost(self, cooperative):
        notif = Notification.objects.create(
            cooperative=cooperative,
            channel=NotificationChannel.SMS,
            notification_type=NotificationType.GENERAL,
            content='Cost test',
        )
        assert notif.cost is None

    def test_clean_validates_matching_cooperative(self, cooperative, farmer):
        farmer.cooperative = cooperative
        farmer.save(update_fields=['cooperative'])
        notif = Notification(
            cooperative=cooperative,
            recipient=farmer,
            channel=NotificationChannel.SMS,
            notification_type=NotificationType.GENERAL,
            content='Test',
        )
        notif.clean()

    def test_clean_raises_on_mismatch(self, cooperative):
        from apps.farmers.models import Farmer
        other_coop = cooperative.__class__.objects.create(
            name='Other Coop', registration_number='OTH001',
            county='Mombasa', produce_type='DAIRY',
            payment_model='FIXED_PRICE', levy_percentage='2.00',
            monthly_fee='100.00', prefix='OTH',
        )
        other_farmer = Farmer.objects.create(
            first_name='Other', last_name='F',
            id_number='ID900', phone_number='+254799999999',
            county='Mombasa', cooperative=other_coop,
        )
        notif = Notification(
            cooperative=cooperative,
            recipient=other_farmer,
            channel=NotificationChannel.SMS,
            notification_type=NotificationType.GENERAL,
            content='Test',
        )
        with pytest.raises(ValidationError, match='cooperative'):
            notif.clean()

    def test_clean_skipped_when_no_recipient_cooperative(self, cooperative):
        notif = Notification(
            cooperative=cooperative,
            channel=NotificationChannel.SMS,
            notification_type=NotificationType.GENERAL,
            content='Test',
        )
        notif.clean()

    def test_soft_delete(self, cooperative):
        notif = Notification.objects.create(
            cooperative=cooperative,
            channel=NotificationChannel.SMS,
            notification_type=NotificationType.GENERAL,
            content='Del test',
        )
        notif.soft_delete()
        assert notif.deleted_at is not None


class TestUSSDSession:
    def test_create(self):
        session = USSDSession.objects.create(
            session_id='SES001',
            phone_number='+254700000001',
        )
        assert session.pk is not None
        assert session.current_menu == 'HOME'

    def test_str(self):
        session = USSDSession.objects.create(
            session_id='SES002',
            phone_number='+254700000002',
        )
        assert 'SES002' in str(session)
        assert '+254700000002' in str(session)

    def test_unique_session_id(self):
        USSDSession.objects.create(
            session_id='UNIQUE_SES',
            phone_number='+254700000001',
        )
        with pytest.raises(Exception):
            USSDSession.objects.create(
                session_id='UNIQUE_SES',
                phone_number='+254700000002',
            )

    def test_last_activity_auto_now(self):
        before = timezone.now()
        session = USSDSession.objects.create(
            session_id='SES003',
            phone_number='+254700000003',
        )
        assert session.last_activity >= before

    def test_menu_change(self):
        session = USSDSession.objects.create(
            session_id='SES004',
            phone_number='+254700000004',
        )
        session.current_menu = 'BALANCE'
        session.save()
        session.refresh_from_db()
        assert session.current_menu == 'BALANCE'
