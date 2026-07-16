import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.base.constants import UserRole
from apps.conftest import (
    CooperativeFactory,
    DeliveryFactory,
    FarmerCooperativeMembershipFactory,
    FarmerFactory,
    NotificationFactory,
    UserFactory,
)
from apps.notifications.models import Notification, USSDSession
from apps.notifications.tasks import (
    cleanup_expired_ussd_sessions,
    send_bulk_sms_task,
    send_sms_task,
)
from apps.notifications.utils import format_delivery_for_ussd, send_sms
from apps.notifications.views import _validate_ussd_ip

pytestmark = pytest.mark.django_db


# =============================================================================
# tasks.py — send_sms_task
# =============================================================================


class TestSendSmsTaskNotFound:
    def test_returns_error_when_notification_does_not_exist(self):
        result = send_sms_task(str(uuid.uuid4()))
        assert result == {'error': 'Notification not found'}


class TestSendSmsTaskAlreadySent:
    def test_skips_already_sent_notification(self):
        notification = NotificationFactory(status='SENT')
        result = send_sms_task(str(notification.id))
        assert result == {'status': 'skipped', 'reason': 'Already sent'}


class TestSendSmsTaskNoRecipientPhone:
    def test_marks_failed_when_no_recipient_phone(self):
        farmer = FarmerFactory(phone_number='')
        notification = NotificationFactory(recipient=farmer)
        send_sms_task(str(notification.id))
        notification.refresh_from_db()
        assert notification.status == 'FAILED'
        assert notification.error_message == 'No recipient phone number'

    def test_marks_failed_when_no_recipient(self):
        notification = NotificationFactory(recipient=None)
        result = send_sms_task(str(notification.id))
        notification.refresh_from_db()
        assert notification.status == 'FAILED'
        assert notification.error_message == 'No recipient phone number'
        assert result == {'error': 'No recipient phone number'}


class TestSendSmsTaskSuccess:
    @patch('apps.notifications.tasks.send_sms')
    def test_marks_sent_on_success(self, mock_send_sms):
        mock_send_sms.return_value = {
            'success': True,
            'external_id': 'ext-123',
            'error': None,
        }
        farmer = FarmerFactory()
        notification = NotificationFactory(recipient=farmer)
        result = send_sms_task(str(notification.id))
        notification.refresh_from_db()
        assert notification.status == 'SENT'
        assert notification.external_id == 'ext-123'
        assert notification.sent_at is not None
        assert result == {'status': 'SENT', 'notification_id': str(notification.id)}

    @patch('apps.notifications.tasks.send_sms')
    def test_handles_empty_external_id(self, mock_send_sms):
        mock_send_sms.return_value = {
            'success': True,
            'external_id': '',
            'error': None,
        }
        farmer = FarmerFactory()
        notification = NotificationFactory(recipient=farmer)
        send_sms_task(str(notification.id))
        notification.refresh_from_db()
        assert notification.external_id == ''


class TestSendSmsTaskRetries:
    @patch('apps.notifications.tasks.send_sms')
    def test_retries_when_failure_and_retries_remaining(self, mock_send_sms):
        mock_send_sms.return_value = {
            'success': False,
            'external_id': None,
            'error': 'timeout',
        }
        farmer = FarmerFactory()
        notification = NotificationFactory(
            recipient=farmer,
            retry_count=0,
            max_retries=3,
        )
        with pytest.raises(Exception):
            send_sms_task(str(notification.id))
        notification.refresh_from_db()
        assert notification.retry_count == 1
        assert notification.error_message == 'timeout'

    @patch('apps.notifications.tasks.send_sms')
    def test_marks_failed_when_max_retries_exceeded(self, mock_send_sms):
        mock_send_sms.return_value = {
            'success': False,
            'external_id': None,
            'error': 'timeout',
        }
        farmer = FarmerFactory()
        notification = NotificationFactory(
            recipient=farmer,
            retry_count=2,
            max_retries=3,
        )
        result = send_sms_task(str(notification.id))
        notification.refresh_from_db()
        assert notification.status == 'FAILED'
        assert notification.error_message == 'timeout'
        assert result == {
            'status': 'FAILED',
            'notification_id': str(notification.id),
            'error': 'timeout',
        }


# =============================================================================
# tasks.py — send_bulk_sms_task
# =============================================================================


class TestSendBulkSmsTask:
    @patch('apps.notifications.tasks.send_sms_task')
    def test_single_chunk(self, mock_task):
        ids = [uuid.uuid4() for _ in range(10)]
        result = send_bulk_sms_task(ids)
        assert result == {'status': 'queued', 'total': 10, 'chunks': 1}
        assert mock_task.delay.call_count == 10

    @patch('apps.notifications.tasks.send_bulk_sms_task.apply_async')
    @patch('apps.notifications.tasks.send_sms_task')
    def test_multiple_chunks(self, mock_task, mock_apply_async):
        ids = [uuid.uuid4() for _ in range(60)]
        result = send_bulk_sms_task(ids)
        assert result == {'status': 'queued', 'total': 60, 'chunks': 2}
        assert mock_task.delay.call_count == 60


# =============================================================================
# tasks.py — cleanup_expired_ussd_sessions
# =============================================================================


class TestCleanupExpiredUssdSessions:
    def test_deletes_old_sessions(self):
        old = USSDSession.objects.create(
            session_id='old',
            phone_number='+254700000001',
        )
        USSDSession.objects.filter(id=old.id).update(
            last_activity=timezone.now() - timedelta(hours=2),
        )

        new = USSDSession.objects.create(
            session_id='new',
            phone_number='+254700000002',
        )

        result = cleanup_expired_ussd_sessions()
        assert result['deleted'] == 1
        assert not USSDSession.objects.filter(id=old.id).exists()
        assert USSDSession.objects.filter(id=new.id).exists()


# =============================================================================
# utils.py — send_sms
# =============================================================================


class TestSendSmsDryRun:
    @patch('apps.notifications.utils.settings')
    def test_returns_success_with_dry_run_id(self, mock_settings):
        mock_settings.NOTIFICATIONS_DRY_RUN = True
        result = send_sms('+254700000000', 'Hello')
        assert result == {'success': True, 'external_id': 'dry-run', 'error': None}


class TestSendSmsNoCredentials:
    @patch('apps.notifications.utils.config', return_value='')
    @patch('apps.notifications.utils.settings')
    def test_returns_failure_when_no_credentials(self, mock_settings, mock_config):
        mock_settings.NOTIFICATIONS_DRY_RUN = False
        result = send_sms('+254700000000', 'Hello')
        assert result == {
            'success': False,
            'external_id': None,
            'error': 'AT credentials not configured',
        }


class TestSendSmsSuccess:
    @patch('apps.notifications.utils.africastalking')
    @patch('apps.notifications.utils.config', side_effect=lambda key, **kw: {'AT_API_KEY': 'key', 'AT_USERNAME': 'user'}[key])
    @patch('apps.notifications.utils.settings')
    def test_returns_external_id_on_success(self, mock_settings, mock_config, mock_at):
        mock_settings.NOTIFICATIONS_DRY_RUN = False
        mock_sms = MagicMock()
        mock_sms.send.return_value = {
            'SMSMessageData': {
                'Recipients': [{'messageId': 'msg-456'}],
            },
        }
        mock_at.SMS = mock_sms
        result = send_sms('+254700000000', 'Hello')
        assert result == {'success': True, 'external_id': 'msg-456', 'error': None}


class TestSendSmsException:
    @patch('apps.notifications.utils.africastalking')
    @patch('apps.notifications.utils.config', side_effect=lambda key, **kw: {'AT_API_KEY': 'key', 'AT_USERNAME': 'user'}[key])
    @patch('apps.notifications.utils.settings')
    def test_returns_error_on_exception(self, mock_settings, mock_config, mock_at):
        mock_settings.NOTIFICATIONS_DRY_RUN = False
        mock_at.initialize.side_effect = RuntimeError('connection failed')
        result = send_sms('+254700000000', 'Hello')
        assert result['success'] is False
        assert result['external_id'] is None
        assert 'connection failed' in result['error']


# =============================================================================
# utils.py — format_delivery_for_ussd
# =============================================================================


class TestFormatDeliveryForUssd:
    def test_kg_delivery_shows_k(self):
        delivery = DeliveryFactory(
            quantity_kg=Decimal('50.00'),
            volume_litres=None,
            grade='A',
            date_delivered=timezone.now().replace(day=15, month=3),
        )
        result = format_delivery_for_ussd(delivery)
        assert result == '15/03 - 50.0K GrA'

    def test_litres_delivery_shows_l(self):
        delivery = DeliveryFactory(
            quantity_kg=None,
            volume_litres=Decimal('120.50'),
            grade='B',
            date_delivered=timezone.now().replace(day=1, month=7),
        )
        result = format_delivery_for_ussd(delivery)
        assert result == '01/07 - 120.5L GrB'

    def test_no_grade_shows_dash(self):
        delivery = DeliveryFactory(
            quantity_kg=Decimal('30.00'),
            volume_litres=None,
            grade='',
            date_delivered=timezone.now().replace(day=25, month=12),
        )
        result = format_delivery_for_ussd(delivery)
        assert result == '25/12 - 30.0K Gr-'


# =============================================================================
# serializers.py — NotificationListSerializer / NotificationDetailSerializer
# =============================================================================


class TestNotificationListSerializer:
    def test_with_recipient(self):
        from apps.notifications.serializers import NotificationListSerializer

        farmer = FarmerFactory(first_name='Jane', last_name='Doe', phone_number='+254700000099')
        notification = NotificationFactory(recipient=farmer)
        data = NotificationListSerializer(notification).data
        assert data['recipient_name'] == 'Jane Doe'
        assert data['recipient_phone'] == '+254700000099'

    def test_without_recipient(self):
        from apps.notifications.serializers import NotificationListSerializer

        notification = NotificationFactory(recipient=None)
        data = NotificationListSerializer(notification).data
        assert data['recipient_name'] is None
        assert data['recipient_phone'] is None


class TestNotificationDetailSerializer:
    def test_with_recipient(self):
        from apps.notifications.serializers import NotificationDetailSerializer

        farmer = FarmerFactory(first_name='John', last_name='Smith', phone_number='+254700000088')
        notification = NotificationFactory(recipient=farmer)
        data = NotificationDetailSerializer(notification).data
        assert data['recipient_name'] == 'John Smith'
        assert data['recipient_phone'] == '+254700000088'

    def test_without_recipient(self):
        from apps.notifications.serializers import NotificationDetailSerializer

        notification = NotificationFactory(recipient=None)
        data = NotificationDetailSerializer(notification).data
        assert data['recipient_name'] is None
        assert data['recipient_phone'] is None


# =============================================================================
# views.py — _validate_ussd_ip
# =============================================================================


def _make_request(remote_addr='127.0.0.1'):
    request = MagicMock()
    request.META = {'REMOTE_ADDR': remote_addr}
    return request


class TestValidateUssdIp:
    @patch('apps.notifications.views.settings')
    def test_empty_whitelist_returns_true(self, mock_settings):
        mock_settings.AFRICASTALKING_CALLBACK_IP_WHITELIST = ''
        assert _validate_ussd_ip(_make_request()) is True

    @patch('apps.notifications.views.settings')
    def test_valid_ip_in_whitelist_returns_true(self, mock_settings):
        mock_settings.AFRICASTALKING_CALLBACK_IP_WHITELIST = '10.0.0.0/8,192.168.1.0/24'
        assert _validate_ussd_ip(_make_request('10.1.2.3')) is True

    @patch('apps.notifications.views.settings')
    def test_ip_not_in_whitelist_returns_false(self, mock_settings):
        mock_settings.AFRICASTALKING_CALLBACK_IP_WHITELIST = '10.0.0.0/8'
        assert _validate_ussd_ip(_make_request('192.168.1.1')) is False

    @patch('apps.notifications.views.settings')
    def test_invalid_remote_addr_returns_false(self, mock_settings):
        mock_settings.AFRICASTALKING_CALLBACK_IP_WHITELIST = '10.0.0.0/8'
        assert _validate_ussd_ip(_make_request('not-an-ip')) is False


# =============================================================================
# views.py — NotificationLogViewSet.get_queryset role scoping
# =============================================================================


class TestNotificationLogViewSetQueryset:
    def _get_viewset_qs(self, user):
        from apps.notifications.views import NotificationLogViewSet

        request = MagicMock()
        request.user = user
        request.cooperative_id = getattr(user, 'cooperative_id', None)
        viewset = NotificationLogViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        return viewset.get_queryset()

    def test_admin_sees_all_notifications(self):
        admin = UserFactory(role=UserRole.ADMIN)
        coop = CooperativeFactory()
        NotificationFactory(cooperative=coop)
        NotificationFactory(cooperative=CooperativeFactory())
        qs = self._get_viewset_qs(admin)
        assert qs.count() == 2

    def test_farmer_sees_only_own_notifications(self):
        user = UserFactory(role=UserRole.FARMER, is_superuser=False, is_staff=False)
        farmer = FarmerFactory(user=user)
        own = NotificationFactory(recipient=farmer, cooperative=farmer.cooperative)
        other_farmer = FarmerFactory()
        NotificationFactory(recipient=other_farmer, cooperative=other_farmer.cooperative)
        qs = self._get_viewset_qs(user)
        assert qs.count() == 1
        assert qs.first().id == own.id

    def test_manager_sees_cooperative_notifications(self):
        coop = CooperativeFactory()
        user = UserFactory(role=UserRole.MANAGER, cooperative=coop, is_superuser=False, is_staff=False)
        notif = NotificationFactory(cooperative=coop)
        other_coop = CooperativeFactory()
        NotificationFactory(cooperative=other_coop)
        qs = self._get_viewset_qs(user)
        assert qs.count() == 1
        assert qs.first().id == notif.id
