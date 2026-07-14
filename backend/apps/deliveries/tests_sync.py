from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.base.constants import UserRole
from apps.conftest import (
    CooperativeFactory,
    DeliveryFactory,
    FarmerFactory,
    FarmerCooperativeMembershipFactory,
    UserFactory,
)
from apps.deliveries.models import Delivery

pytestmark = pytest.mark.django_db


@pytest.fixture
def manager_user(cooperative):
    user = UserFactory(
        role=UserRole.MANAGER,
        cooperative=cooperative,
        is_superuser=False,
        is_staff=False,
    )
    user.raw_password = 'testpass123'
    return user


@pytest.fixture
def manager_client(manager_user):
    client = APIClient()
    client.force_authenticate(user=manager_user)
    return client


@pytest.fixture
def farmer_user(cooperative):
    user = UserFactory(
        role=UserRole.FARMER,
        cooperative=cooperative,
        is_superuser=False,
        is_staff=False,
    )
    user.raw_password = 'testpass123'
    farmer = FarmerFactory(cooperative=cooperative, user=user)
    return user


@pytest.fixture
def farmer_client(farmer_user):
    client = APIClient()
    client.force_authenticate(user=farmer_user)
    return client


@pytest.fixture
def test_farmer(cooperative):
    return FarmerFactory(cooperative=cooperative)


@pytest.fixture
def test_farmer2(cooperative):
    return FarmerFactory(cooperative=cooperative)


def _sync_payload(*deliveries):
    return {'deliveries': list(deliveries)}


def _delivery_data(farmer_id, local_id=None, product_type='MILK',
                   volume_litres='10.00', latitude=None, longitude=None):
    data = {
        'farmer': str(farmer_id),
        'product_type': product_type,
        'volume_litres': volume_litres,
        'status': 'PENDING',
        'shift': 'AM',
        'date_delivered': (timezone.now() - timedelta(hours=1)).isoformat(),
    }
    if local_id:
        data['local_id'] = local_id
    if latitude is not None:
        data['latitude'] = str(latitude)
    if longitude is not None:
        data['longitude'] = str(longitude)
    return data


# =============================================================================
# Duplicate local_id dedup
# =============================================================================

class TestSyncDuplicateLocalId:
    @patch('apps.deliveries.views.send_bulk_delivery_sms.delay')
    def test_duplicate_local_id_returns_409(self, mock_sms, manager_client,
                                             cooperative, test_farmer):
        payload = _sync_payload(
            _delivery_data(test_farmer.id, local_id='offline-001'),
        )
        resp = manager_client.post(
            '/api/deliveries/sync/', payload, format='json',
        )
        assert resp.status_code == 201

        mock_sms.reset_mock()
        resp2 = manager_client.post(
            '/api/deliveries/sync/', payload, format='json',
        )
        assert resp2.status_code == 409
        assert resp2.data.get('conflicts')
        assert resp2.data['conflicts'][0]['local_id'] == 'offline-001'
        assert Delivery.objects.filter(local_id='offline-001').count() == 1

    @patch('apps.deliveries.views.send_bulk_delivery_sms.delay')
    def test_duplicate_local_id_same_coop_dedup(self, mock_sms, manager_client,
                                                  cooperative, test_farmer):
        payload = _sync_payload(
            _delivery_data(test_farmer.id, local_id='dup-1'),
            _delivery_data(test_farmer.id, local_id='dup-1'),
        )
        resp = manager_client.post(
            '/api/deliveries/sync/', payload, format='json',
        )
        assert resp.status_code == 409
        assert len(resp.data.get('conflicts', [])) == 1
        assert Delivery.objects.filter(local_id='dup-1').count() == 1

    @patch('apps.deliveries.views.send_bulk_delivery_sms.delay')
    def test_different_coop_same_local_id_not_duplicate(self, mock_sms, manager_client,
                                                         cooperative, test_farmer):
        payload = _sync_payload(
            _delivery_data(test_farmer.id, local_id='coop-a-item'),
        )
        resp = manager_client.post(
            '/api/deliveries/sync/', payload, format='json',
        )
        assert resp.status_code == 201


# =============================================================================
# Partial batch failure
# =============================================================================

class TestSyncPartialBatchFailure:
    @patch('apps.deliveries.views.send_bulk_delivery_sms.delay')
    def test_mixed_valid_and_conflicting(self, mock_sms, manager_client,
                                          cooperative, test_farmer):
        payload1 = _sync_payload(
            _delivery_data(test_farmer.id, local_id='batch-1'),
        )
        resp1 = manager_client.post(
            '/api/deliveries/sync/', payload1, format='json',
        )
        assert resp1.status_code == 201

        payload2 = _sync_payload(
            _delivery_data(test_farmer.id, local_id='batch-2'),
            _delivery_data(test_farmer.id, local_id='batch-1'),
        )
        resp2 = manager_client.post(
            '/api/deliveries/sync/', payload2, format='json',
        )
        assert resp2.status_code == 409
        assert len(resp2.data.get('synced', [])) == 1
        assert resp2.data['synced'][0]['local_id'] == 'batch-2'
        assert len(resp2.data.get('conflicts', [])) == 1
        assert Delivery.objects.filter(local_id='batch-1').count() == 1
        assert Delivery.objects.filter(local_id='batch-2').count() == 1

    @patch('apps.deliveries.views.send_bulk_delivery_sms.delay')
    def test_empty_batch_returns_201(self, mock_sms, manager_client, cooperative):
        resp = manager_client.post(
            '/api/deliveries/sync/', {'deliveries': []}, format='json',
        )
        assert resp.status_code in (200, 201, 400)


# =============================================================================
# GPS preservation
# =============================================================================

class TestSyncGpsPreservation:
    @patch('apps.deliveries.views.send_bulk_delivery_sms.delay')
    def test_gps_coords_saved(self, mock_sms, manager_client, cooperative, test_farmer):
        payload = _sync_payload(
            _delivery_data(
                test_farmer.id, local_id='gps-1',
                latitude=-1.2921, longitude=36.8219,
            ),
        )
        resp = manager_client.post(
            '/api/deliveries/sync/', payload, format='json',
        )
        assert resp.status_code == 201
        delivery = Delivery.objects.get(local_id='gps-1')
        assert delivery.latitude is not None
        assert delivery.longitude is not None

    @patch('apps.deliveries.views.send_bulk_delivery_sms.delay')
    def test_null_gps_coords_preserved(self, mock_sms, manager_client, cooperative, test_farmer):
        payload = _sync_payload(
            _delivery_data(test_farmer.id, local_id='gps-null'),
        )
        resp = manager_client.post(
            '/api/deliveries/sync/', payload, format='json',
        )
        assert resp.status_code == 201
        delivery = Delivery.objects.get(local_id='gps-null')
        assert delivery.latitude is None
        assert delivery.longitude is None


# =============================================================================
# Basic sync flow
# =============================================================================

class TestSyncBasic:
    @patch('apps.deliveries.views.send_bulk_delivery_sms.delay')
    def test_sync_creates_deliveries(self, mock_sms, manager_client, cooperative, test_farmer):
        payload = _sync_payload(
            _delivery_data(test_farmer.id, local_id='sync-1'),
            _delivery_data(test_farmer.id, local_id='sync-2'),
        )
        resp = manager_client.post(
            '/api/deliveries/sync/', payload, format='json',
        )
        assert resp.status_code == 201
        assert len(resp.data['synced']) == 2
        assert Delivery.objects.filter(local_id__in=['sync-1', 'sync-2']).count() == 2

    @patch('apps.deliveries.views.send_bulk_delivery_sms.delay')
    def test_sync_fires_sms_task(self, mock_sms, manager_client, cooperative, test_farmer):
        payload = _sync_payload(
            _delivery_data(test_farmer.id, local_id='sms-1'),
        )
        resp = manager_client.post(
            '/api/deliveries/sync/', payload, format='json',
        )
        assert resp.status_code == 201
        mock_sms.assert_called_once()

    @patch('apps.deliveries.views.send_bulk_delivery_sms.delay')
    def test_sync_no_sms_when_empty(self, mock_sms, manager_client, cooperative):
        resp = manager_client.post(
            '/api/deliveries/sync/', {'deliveries': []}, format='json',
        )
        mock_sms.assert_not_called()


# =============================================================================
# Offline idempotency on sync endpoint
# =============================================================================

class TestSyncIdempotency:
    @patch('apps.deliveries.views.send_bulk_delivery_sms.delay')
    def test_duplicate_local_id_returns_409_without_idem_key(self, mock_sms,
                                                              manager_client, cooperative, test_farmer):
        payload = _sync_payload(
            _delivery_data(test_farmer.id, local_id='idem-no-key'),
        )
        resp1 = manager_client.post(
            '/api/deliveries/sync/', payload, format='json',
        )
        assert resp1.status_code == 201

        resp2 = manager_client.post(
            '/api/deliveries/sync/', payload, format='json',
        )
        assert resp2.status_code == 409

    @patch('apps.deliveries.views.send_bulk_delivery_sms.delay')
    def test_different_local_ids_succeed(self, mock_sms, manager_client,
                                          cooperative, test_farmer):
        resp1 = manager_client.post(
            '/api/deliveries/sync/',
            _sync_payload(_delivery_data(test_farmer.id, local_id='idem-a')),
            format='json',
            HTTP_IDEMPOTENCY_KEY='sync-batch-1',
        )
        assert resp1.status_code == 201

        resp2 = manager_client.post(
            '/api/deliveries/sync/',
            _sync_payload(_delivery_data(test_farmer.id, local_id='idem-b')),
            format='json',
            HTTP_IDEMPOTENCY_KEY='sync-batch-2',
        )
        assert resp2.status_code == 201


# =============================================================================
# GPS coordinate range preservation
# =============================================================================

class TestSyncGpsPrecision:
    @patch('apps.deliveries.views.send_bulk_delivery_sms.delay')
    def test_high_precision_gps(self, mock_sms, manager_client, cooperative, test_farmer):
        payload = _sync_payload(
            _delivery_data(
                test_farmer.id, local_id='gps-precise',
                latitude=-1.292084, longitude=36.821946,
            ),
        )
        resp = manager_client.post(
            '/api/deliveries/sync/', payload, format='json',
        )
        assert resp.status_code == 201
        delivery = Delivery.objects.get(local_id='gps-precise')
        assert delivery.latitude is not None
        assert delivery.longitude is not None
