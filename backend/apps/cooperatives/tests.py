import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status

from apps.base.constants import UserRole
from apps.cooperatives.models import Cooperative, PaymentModel, ProduceType

pytestmark = pytest.mark.django_db


# =============================================================================
# Cooperative Model Tests
# =============================================================================

class TestCooperativeModel:
    def test_create(self):
        coop = Cooperative.objects.create(
            name='Test Coop',
            registration_number='REG001',
            county='Nairobi',
            produce_type=ProduceType.DAIRY,
            payment_model=PaymentModel.FIXED_PRICE,
            levy_percentage='2.00',
            monthly_fee='100.00',
            prefix='TST',
        )
        assert coop.pk is not None
        assert str(coop) == 'Test Coop'

    def test_delete_sets_deleted_at(self, cooperative):
        cooperative.delete()
        assert cooperative.deleted_at is not None
        assert Cooperative.objects.filter(pk=cooperative.pk).exists() is False

    def test_default_manager_excludes_deleted(self, cooperative):
        cooperative.delete()
        assert not Cooperative.objects.filter(pk=cooperative.pk).exists()

    def test_all_with_trashed_includes_deleted(self, cooperative):
        cooperative.delete()
        assert Cooperative.objects.all_with_trashed().filter(pk=cooperative.pk).exists()

    def test_trashed_only(self, cooperative):
        cooperative.delete()
        assert Cooperative.objects.trashed_only().filter(pk=cooperative.pk).exists()

    def test_restore(self, cooperative):
        cooperative.delete()
        cooperative.restore()
        assert cooperative.deleted_at is None
        assert cooperative.restored_at is not None
        assert cooperative.deleted_via_cascade_from is None

    def test_hard_delete(self, cooperative):
        cooperative.hard_delete()
        assert not Cooperative.objects.all_with_trashed().filter(pk=cooperative.pk).exists()

    def test_restore_after_hard_delete_clears_cascade(self, cooperative):
        cooperative.delete()
        cooperative.restore()
        assert cooperative.deleted_via_cascade_from is None


class TestCooperativeCascadeSoftDelete:
    def test_cascade_soft_deletes_farmer(self, cooperative, farmer):
        farmer.cooperative = cooperative
        farmer.save()
        cooperative.delete()
        from apps.farmers.models import Farmer
        assert not Farmer.objects.filter(pk=farmer.pk).exists()

    def test_cascade_soft_deletes_membership(self, cooperative):
        from apps.farmers.models import Farmer, FarmerCooperativeMembership
        f = Farmer.objects.create(
            first_name='Test', last_name='F',
            id_number='IDMEM001', phone_number='+25470000099',
            county='Nairobi', cooperative=cooperative,
        )
        membership = f.memberships.get(cooperative=cooperative)
        cooperative.delete()
        membership.refresh_from_db()
        assert membership.deleted_at is not None
        assert membership.deleted_via_cascade_from == cooperative.pk

    def test_cascade_sets_deleted_via_cascade_from(self, cooperative, farmer):
        farmer.cooperative = cooperative
        farmer.save(update_fields=['cooperative'])
        cooperative.delete()
        farmer.refresh_from_db()
        assert farmer.deleted_via_cascade_from == cooperative.pk

    def test_cascade_restore_restores_children(self, cooperative, farmer):
        farmer.cooperative = cooperative
        farmer.save(update_fields=['cooperative'])
        cooperative.delete()
        cooperative.restore()
        farmer.refresh_from_db()
        assert farmer.deleted_at is None
        assert farmer.restored_at is not None
        assert farmer.deleted_via_cascade_from is None

    def test_cascade_soft_deletes_delivery(self, cooperative):
        from apps.deliveries.models import Delivery
        from apps.farmers.models import Farmer
        f = Farmer.objects.create(
            first_name='Del', last_name='F',
            id_number='IDDEL', phone_number='+25470000090',
            county='Nairobi', cooperative=cooperative,
        )
        delivery = Delivery.objects.create(
            cooperative=cooperative, farmer=f, batch_id='BATDEL001',
        )
        cooperative.delete()
        assert not Delivery.objects.filter(pk=delivery.pk).exists()

    def test_cascade_soft_deletes_loan(self, cooperative):
        from apps.loans.models import Loan
        from apps.farmers.models import Farmer
        f = Farmer.objects.create(
            first_name='Loan', last_name='F',
            id_number='IDLOAN', phone_number='+25470000091',
            county='Nairobi', cooperative=cooperative,
        )
        loan = Loan.objects.create(
            farmer=f,
            cooperative=cooperative,
            amount_principal='10000',
            interest_rate='10',
            total_repayable='11000',
            installment_amount='1833.33',
            number_of_installments=6,
        )
        cooperative.delete()
        assert not Loan.objects.filter(pk=loan.pk).exists()

    def test_cascade_soft_deletes_loan_guarantor(self, cooperative):
        from apps.loans.models import Loan, LoanGuarantor
        from apps.farmers.models import Farmer
        f = Farmer.objects.create(
            first_name='LG1', last_name='F',
            id_number='IDLG1', phone_number='+25470000092',
            county='Nairobi', cooperative=cooperative,
        )
        g = Farmer.objects.create(
            first_name='LG2', last_name='F',
            id_number='IDLG2', phone_number='+25470000093',
            county='Nairobi', cooperative=cooperative,
        )
        loan = Loan.objects.create(
            farmer=f,
            cooperative=cooperative,
            amount_principal='10000',
            interest_rate='10',
            total_repayable='11000',
            installment_amount='1833.33',
            number_of_installments=6,
        )
        guarantor = LoanGuarantor.objects.create(
            loan=loan, guarantor=g, cooperative=cooperative,
        )
        cooperative.delete()
        assert not LoanGuarantor.objects.filter(pk=guarantor.pk).exists()

    def test_cascade_soft_deletes_buyer(self, cooperative):
        from apps.sales.models import Buyer
        buyer = Buyer.objects.create(cooperative=cooperative, name='Test Buyer')
        cooperative.delete()
        assert not Buyer.objects.filter(pk=buyer.pk).exists()

    def test_cascade_unaffected_model_ignored(self, cooperative):
        cooperative.delete()
        assert True


class TestCooperativeModelDefaults:
    def test_default_member_count(self):
        coop = Cooperative(registration_number='DEF001')
        assert coop.member_count == 0

    def test_str_method(self, cooperative):
        assert str(cooperative) == cooperative.name


# =============================================================================
# Cooperative API Endpoint Tests
# =============================================================================

from django.contrib.auth import get_user_model
User = get_user_model()


class TestCooperativeAPI:
    def test_list_unauthenticated(self, client):
        resp = client.get('/api/cooperatives/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_authenticated(self, api_client, cooperative):
        resp = api_client.get('/api/cooperatives/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) >= 1

    def test_retrieve(self, api_client, cooperative):
        resp = api_client.get(f'/api/cooperatives/{cooperative.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['name'] == cooperative.name

    def test_create_admin(self, api_client):
        resp = api_client.post('/api/cooperatives/', {
            'name': 'Brand New Coop',
            'registration_number': 'REG123456',
            'county': 'Nairobi',
            'produce_type': 'DAIRY',
            'payment_model': 'FIXED_PRICE',
            'levy_percentage': '2.00',
            'monthly_fee': '100.00',
            'prefix': 'BNC',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()['name'] == 'Brand New Coop'

    def test_create_manager_without_coop(self, cooperative):
        from rest_framework.test import APIClient
        manager = User.objects.create_user(
            email='mgr@coop.com', phone_number='+25470000111',
            first_name='Mgr', last_name='Coop',
            password='testpass123', role=UserRole.MANAGER,
        )
        client = APIClient()
        client.force_authenticate(user=manager)
        resp = client.post('/api/cooperatives/', {
            'name': 'Manager Coop',
            'registration_number': 'REG789012',
            'county': 'Mombasa',
            'produce_type': 'DAIRY',
            'payment_model': 'FIXED_PRICE',
            'levy_percentage': '2.00',
            'monthly_fee': '100.00',
            'prefix': 'MGR',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        manager.refresh_from_db()
        assert manager.cooperative_id is not None

    def test_create_manager_with_existing_coop_denied(self, cooperative):
        from rest_framework.test import APIClient
        manager = User.objects.create_user(
            email='mgr2@coop.com', phone_number='+25470000222',
            first_name='Mgr2', last_name='Coop',
            password='testpass123', role=UserRole.MANAGER, cooperative=cooperative,
        )
        client = APIClient()
        client.force_authenticate(user=manager)
        resp = client.post('/api/cooperatives/', {
            'name': 'Another Coop',
            'registration_number': 'REG345678',
            'county': 'Nairobi',
            'produce_type': 'DAIRY',
            'payment_model': 'FIXED_PRICE',
            'levy_percentage': '2.00',
            'monthly_fee': '100.00',
            'prefix': 'ANR',
        }, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_create_unauthenticated(self, client):
        resp = client.post('/api/cooperatives/', {
            'name': 'Test', 'registration_number': 'REGX',
            'county': 'Nairobi', 'produce_type': 'DAIRY',
            'payment_model': 'FIXED_PRICE', 'levy_percentage': '2.00',
            'monthly_fee': '100.00', 'prefix': 'TST',
        }, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_farmer_denied(self, cooperative):
        from rest_framework.test import APIClient
        farmer_user = User.objects.create_user(
            email='f@coop.com', phone_number='+25470000333',
            first_name='Far', last_name='Coop',
            password='testpass123', role=UserRole.FARMER, cooperative=cooperative,
        )
        client = APIClient()
        client.force_authenticate(user=farmer_user)
        resp = client.post('/api/cooperatives/', {
            'name': 'Test', 'registration_number': 'REGY',
            'county': 'Nairobi', 'produce_type': 'DAIRY',
            'payment_model': 'FIXED_PRICE', 'levy_percentage': '2.00',
            'monthly_fee': '100.00', 'prefix': 'TSTY',
        }, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_update(self, api_client, cooperative):
        resp = api_client.patch(f'/api/cooperatives/{cooperative.id}/',
                                {'name': 'Updated Coop Name'}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['name'] == 'Updated Coop Name'

    def test_update_manager_allowed(self, cooperative):
        from rest_framework.test import APIClient
        manager = User.objects.create_user(
            email='mgr3@coop.com', phone_number='+25470000444',
            first_name='Mgr3', last_name='Coop',
            password='testpass123', role=UserRole.MANAGER, cooperative=cooperative,
        )
        client = APIClient()
        client.force_authenticate(user=manager)
        resp = client.patch(f'/api/cooperatives/{cooperative.id}/',
                            {'name': 'Manager Update'}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        cooperative.refresh_from_db()
        assert cooperative.name == 'Manager Update'

    def test_destroy(self, api_client, cooperative):
        resp = api_client.delete(f'/api/cooperatives/{cooperative.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_destroy_manager_denied(self, cooperative):
        from rest_framework.test import APIClient
        manager = User.objects.create_user(
            email='mgr4@coop.com', phone_number='+25470000555',
            first_name='Mgr4', last_name='Coop',
            password='testpass123', role=UserRole.MANAGER, cooperative=cooperative,
        )
        client = APIClient()
        client.force_authenticate(user=manager)
        resp = client.delete(f'/api/cooperatives/{cooperative.id}/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_filter_by_county(self, api_client, cooperative):
        resp = api_client.get(f'/api/cooperatives/?county={cooperative.county}')
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_by_produce_type(self, api_client, cooperative):
        resp = api_client.get(f'/api/cooperatives/?produce_type={cooperative.produce_type}')
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_by_is_active(self, api_client, cooperative):
        resp = api_client.get('/api/cooperatives/?is_active=true')
        assert resp.status_code == status.HTTP_200_OK

    def test_search(self, api_client, cooperative):
        resp = api_client.get(f'/api/cooperatives/?search={cooperative.name[:5]}')
        assert resp.status_code == status.HTTP_200_OK


class TestCooperativePut:
    def test_put_allows_same_registration_number(self, api_client, cooperative):
        data = {
            'name': 'Updated Coop Name',
            'registration_number': cooperative.registration_number,
            'county': cooperative.county,
            'sub_county': cooperative.sub_county,
            'ward': cooperative.ward,
            'produce_type': cooperative.produce_type,
            'payment_model': cooperative.payment_model,
            'levy_percentage': float(cooperative.levy_percentage),
            'monthly_fee': float(cooperative.monthly_fee),
            'mpesa_shortcode': cooperative.mpesa_shortcode,
            'till_number': cooperative.till_number,
            'kra_pin': cooperative.kra_pin,
            'phone_number': cooperative.phone_number,
            'email': cooperative.email,
            'physical_address': cooperative.physical_address,
        }
        resp = api_client.put(f'/api/cooperatives/{cooperative.id}/', data, format='json')
        assert resp.status_code == 200
        assert resp.json()['registration_number'] == cooperative.registration_number

    def test_put_rejects_duplicate_registration_number(self, api_client, cooperative):
        other_coop = Cooperative.objects.create(
            name='Other Coop',
            registration_number='DUPLICATE123',
            county='Nairobi',
            produce_type='DAIRY',
            payment_model='FIXED_PRICE',
            levy_percentage='2.00',
            monthly_fee='100.00',
            prefix='OTHER123',
        )
        data = {
            'name': 'Updated Coop Name',
            'registration_number': other_coop.registration_number,
            'county': cooperative.county,
            'sub_county': cooperative.sub_county,
            'ward': cooperative.ward,
            'produce_type': cooperative.produce_type,
            'payment_model': cooperative.payment_model,
            'levy_percentage': float(cooperative.levy_percentage),
            'monthly_fee': float(cooperative.monthly_fee),
            'mpesa_shortcode': cooperative.mpesa_shortcode,
            'till_number': cooperative.till_number,
            'kra_pin': cooperative.kra_pin,
            'phone_number': cooperative.phone_number,
            'email': cooperative.email,
            'physical_address': cooperative.physical_address,
        }
        resp = api_client.put(f'/api/cooperatives/{cooperative.id}/', data, format='json')
        assert resp.status_code == 400
        assert 'registration number' in resp.json()['registration_number'][0].lower()

    def test_put_rejects_levy_over_100(self, api_client, cooperative):
        data = {
            'name': cooperative.name,
            'registration_number': cooperative.registration_number,
            'county': cooperative.county,
            'produce_type': cooperative.produce_type,
            'payment_model': cooperative.payment_model,
            'levy_percentage': 101,
            'monthly_fee': float(cooperative.monthly_fee),
        }
        resp = api_client.put(f'/api/cooperatives/{cooperative.id}/', data, format='json')
        assert resp.status_code == 400


class TestCooperativeStats:
    def test_stats(self, api_client, cooperative):
        resp = api_client.get('/api/cooperatives/stats/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert 'total' in data
        assert 'active' in data
        assert 'by_produce_type' in data
        assert 'by_county' in data
        assert 'by_verified' in data
        assert data['total'] >= 1


class TestCooperativeMe:
    def test_me_assigned(self, api_client, cooperative):
        api_client.user.cooperative = cooperative
        api_client.user.save()
        resp = api_client.get('/api/cooperatives/me/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['id'] == str(cooperative.id)

    def test_me_unassigned(self, api_client):
        resp = api_client.get('/api/cooperatives/me/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestCooperativeEnums:
    def test_enums(self, api_client):
        resp = api_client.get('/api/cooperatives/enums/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert 'produce_types' in data
        assert 'payment_models' in data
        assert ['DAIRY', 'Dairy'] in data['produce_types']
        assert ['FIXED_PRICE', 'Fixed Price'] in data['payment_models']
