import uuid
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status

from apps.base.constants import UserRole
from apps.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    USSDSession,
)

pytestmark = pytest.mark.django_db


# =============================================================================
# Notification Model Tests
# =============================================================================

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


# =============================================================================
# Notification API Endpoint Tests
# =============================================================================

from django.contrib.auth import get_user_model
User = get_user_model()


class TestNotificationLogAPI:
    def test_list_unauthenticated(self, client):
        resp = client.get('/api/notifications/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_authenticated(self, api_client, notification):
        resp = api_client.get('/api/notifications/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) >= 1

    def test_retrieve(self, api_client, notification):
        resp = api_client.get(f'/api/notifications/{notification.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['id'] == str(notification.id)

    def test_retrieve_not_found(self, api_client):
        resp = api_client.get(f'/api/notifications/{uuid.uuid4()}/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_list_permission_farmer_denied(self, cooperative, notification):
        from rest_framework.test import APIClient
        farmer_user = User.objects.create_user(
            email='f@notif.com', phone_number='+25470000111',
            password='testpass123', role=UserRole.FARMER, cooperative=cooperative,
        )
        client = APIClient()
        client.force_authenticate(user=farmer_user)
        resp = client.get('/api/notifications/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_list_permission_manager_allowed(self, cooperative, notification):
        from rest_framework.test import APIClient
        manager = User.objects.create_user(
            email='mgr@notif.com', phone_number='+25470000222',
            password='testpass123', role=UserRole.MANAGER, cooperative=cooperative,
        )
        client = APIClient()
        client.force_authenticate(user=manager)
        resp = client.get('/api/notifications/')
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_by_channel(self, api_client, notification):
        resp = api_client.get(f'/api/notifications/?search={notification.channel}')
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_by_status(self, api_client, notification):
        resp = api_client.get(f'/api/notifications/?search={notification.status}')
        assert resp.status_code == status.HTTP_200_OK

    def test_create_not_allowed(self, api_client):
        resp = api_client.post('/api/notifications/', {'content': 'test'}, format='json')
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_update_not_allowed(self, api_client, notification):
        resp = api_client.patch(f'/api/notifications/{notification.id}/',
                                {'content': 'x'}, format='json')
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_not_allowed(self, api_client, notification):
        resp = api_client.delete(f'/api/notifications/{notification.id}/')
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestUSSDRedirect:
    def test_ussd_callback_invalid_service_code(self, client):
        resp = client.post('/api/callback/ussd/', {
            'sessionId': 'SESSION001',
            'serviceCode': '*384*99999#',
            'phoneNumber': '+254700000001',
            'text': '',
        })
        assert resp.status_code == status.HTTP_200_OK
        assert b'Invalid service code' in resp.content

    @pytest.mark.skip(reason='Requires configured service code')
    def test_ussd_callback_valid(self, client):
        pass
