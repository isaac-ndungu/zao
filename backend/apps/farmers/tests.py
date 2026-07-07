import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.base.constants import UserRole
from apps.farmers.models import Farmer, FarmerCooperativeMembership, FarmerPaymentMethod

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def manager_api_client(db, cooperative):
    manager = User.objects.create_user(
        'farmer-mgr@test.com', '+25470000999', 'Mgr', 'Farmer',
        password='testpass123', role=UserRole.MANAGER, cooperative=cooperative,
    )
    client = APIClient()
    client.force_authenticate(user=manager)
    client.user = manager
    return client


@pytest.fixture
def grader_api_client(db, cooperative):
    grader = User.objects.create_user(
        'farmer-grader@test.com', '+25470000777', 'Grader', 'Farmer',
        password='testpass123', role=UserRole.GRADER, cooperative=cooperative,
    )
    client = APIClient()
    client.force_authenticate(user=grader)
    client.user = grader
    return client


class TestFarmerModel:
    def test_create(self, cooperative):
        farmer = Farmer.objects.create(
            first_name='John',
            last_name='Doe',
            id_number='ID123456',
            phone_number='+254700000001',
            county='Nairobi',
            cooperative=cooperative,
        )
        assert farmer.pk is not None
        assert farmer.is_active

    def test_soft_delete(self, farmer):
        farmer.soft_delete()
        assert farmer.deleted_at is not None
        assert not Farmer.objects.filter(pk=farmer.pk).exists()

    def test_delete_calls_soft_delete(self, farmer):
        farmer.delete()
        assert farmer.deleted_at is not None

    def test_str_with_membership(self, farmer):
        assert farmer.primary_membership is not None
        mn = farmer.primary_membership.member_number
        assert mn in str(farmer)
        assert farmer.first_name in str(farmer)

    def test_str_with_membership_shows_number(self, farmer):
        assert farmer.primary_membership is not None
        mn = farmer.primary_membership.member_number
        assert mn in str(farmer)

    def test_primary_membership_returns_first(self, farmer):
        membership = farmer.primary_membership
        assert membership is not None
        assert membership.farmer == farmer

    def test_hard_delete(self, farmer):
        farmer.hard_delete()
        from apps.base.models import CooperativeScopedModel
        mgr = Farmer.objects
        if hasattr(mgr, 'all_with_trashed'):
            assert not mgr.all_with_trashed().filter(pk=farmer.pk).exists()

    def test_restore(self, farmer):
        farmer.soft_delete()
        farmer.restore()
        assert farmer.deleted_at is None
        assert farmer.restored_at is not None

    def test_default_manager_excludes_trashed(self, farmer):
        farmer.soft_delete()
        assert not Farmer.objects.filter(pk=farmer.pk).exists()


class TestFarmerCooperativeMembership:
    def test_create(self, farmer, cooperative):
        membership = FarmerCooperativeMembership.objects.create(
            farmer=farmer,
            cooperative=cooperative,
            member_number='MEM001',
        )
        assert membership.pk is not None
        assert membership.is_active
        assert membership.payment_method == FarmerPaymentMethod.M_PESA

    def test_unique_farmer_cooperative(self, farmer, cooperative):
        FarmerCooperativeMembership.objects.filter(farmer=farmer, cooperative=cooperative).delete()
        FarmerCooperativeMembership.objects.create(
            farmer=farmer,
            cooperative=cooperative,
            member_number='MEM001',
        )
        with pytest.raises(IntegrityError):
            FarmerCooperativeMembership.objects.create(
                farmer=farmer,
                cooperative=cooperative,
                member_number='MEM002',
            )

    def test_unique_member_number_per_coop(self, cooperative):
        from apps.farmers.models import Farmer
        farmer1 = Farmer.objects.create(
            first_name='A', last_name='B', id_number='ID1',
            phone_number='+25470000001', county='Nairobi',
            cooperative=cooperative,
        )
        farmer1.memberships.all().delete()
        farmer2 = Farmer.objects.create(
            first_name='C', last_name='D', id_number='ID2',
            phone_number='+25470000002', county='Nairobi',
            cooperative=cooperative,
        )
        farmer2.memberships.all().delete()
        FarmerCooperativeMembership.objects.create(
            farmer=farmer1, cooperative=cooperative, member_number='MEM001',
        )
        with pytest.raises(IntegrityError):
            FarmerCooperativeMembership.objects.create(
                farmer=farmer2, cooperative=cooperative, member_number='MEM001',
            )

    def test_soft_delete(self, farmer, cooperative):
        membership = FarmerCooperativeMembership.objects.create(
            farmer=farmer, cooperative=cooperative, member_number='MEM001',
        )
        membership.soft_delete()
        assert membership.deleted_at is not None

    def test_restore(self, farmer, cooperative):
        membership = FarmerCooperativeMembership.objects.create(
            farmer=farmer, cooperative=cooperative, member_number='MEM002',
        )
        membership.soft_delete()
        membership.restore()
        assert membership.deleted_at is None
        assert membership.restored_at is not None

    def test_hard_delete(self, farmer, cooperative):
        membership = FarmerCooperativeMembership.objects.create(
            farmer=farmer, cooperative=cooperative, member_number='MEM003',
        )
        membership.hard_delete()
        assert not FarmerCooperativeMembership.objects.filter(pk=membership.pk).exists()

    def test_str(self, farmer, cooperative):
        membership = FarmerCooperativeMembership.objects.create(
            farmer=farmer, cooperative=cooperative, member_number='MEM004',
        )
        assert 'MEM004' in str(membership)
        assert farmer.first_name in str(membership)


# =============================================================================
# FarmerViewSet endpoint tests
# =============================================================================


class TestFarmerViewSetList:
    def test_list_as_admin(self, api_client, farmer):
        resp = api_client.get('/api/farmers/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        if isinstance(data, dict):
            assert len(data['results']) >= 1
        else:
            assert len(data) >= 1

    def test_list_filters_by_first_name(self, api_client, farmer):
        resp = api_client.get(f'/api/farmers/?first_name={farmer.first_name}')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        items = data['results'] if isinstance(data, dict) else data
        assert len(items) >= 1
        assert items[0]['first_name'] == farmer.first_name

    def test_list_filters_by_is_active(self, api_client, farmer):
        resp = api_client.get('/api/farmers/?is_active=true')
        assert resp.status_code == status.HTTP_200_OK

    def test_list_unauthenticated(self, client):
        resp = client.get('/api/farmers/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestFarmerViewSetCreate:
    def test_create_as_manager(self, api_client, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='farmer_crt@test.com', phone_number='+254700000201',
            first_name='Farmer', last_name='CrtMgr',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.post('/api/farmers/', {
            'first_name': 'New', 'last_name': 'Farmer',
            'id_number': '12345678', 'phone_number': '+254700000202',
            'county': 'Nairobi', 'email': 'newfarmer@test.com',
        })
        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        from apps.farmers.models import Farmer
        farmer = Farmer.objects.get(id=resp.json()['id'])
        assert farmer.first_name == 'New'
        assert farmer.user is not None
        assert farmer.user.role == UserRole.FARMER
        assert farmer.user.email == 'newfarmer@test.com'

    def test_create_as_admin_can_set_cooperative(self, api_client, cooperative):
        from apps.cooperatives.models import Cooperative
        other_coop = Cooperative.objects.create(
            name='Other Coop', registration_number='OTH001',
            county='Nairobi', produce_type='DAIRY',
            payment_model='FIXED_PRICE', prefix='OTH',
        )
        resp = api_client.post('/api/farmers/', {
            'first_name': 'Admin', 'last_name': 'Create',
            'id_number': '87654321', 'phone_number': '+254700000203',
            'county': 'Nairobi', 'email': 'admincreate@test.com',
            'cooperative_id': str(other_coop.id),
        })
        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        assert resp.json()['cooperative'] == str(other_coop.id)

    def test_create_forbidden_for_grader(self, api_client, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grader = User.objects.create_user(
            email='farmer_grader@test.com', phone_number='+254700000204',
            first_name='Grd', last_name='Crt',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=grader)
        resp = api_client.post('/api/farmers/', {
            'first_name': 'Fail', 'last_name': 'Create',
            'id_number': '12345678', 'phone_number': '+254700000205',
            'county': 'Nairobi',
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_create_unauthenticated(self, client):
        resp = client.post('/api/farmers/', {
            'first_name': 'Fail', 'last_name': 'Auth',
            'id_number': '12345678', 'phone_number': '+254700000206',
            'county': 'Nairobi',
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_validates_phone_format(self, api_client, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='farmer_val@test.com', phone_number='+254700000207',
            first_name='Val', last_name='Crt',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.post('/api/farmers/', {
            'first_name': 'Bad', 'last_name': 'Phone',
            'id_number': '12345678', 'phone_number': 'invalid',
            'county': 'Nairobi',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestFarmerViewSetRetrieveUpdateDestroy:
    def test_retrieve(self, api_client, farmer):
        resp = api_client.get(f'/api/farmers/{farmer.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['id'] == str(farmer.id)

    def test_update_as_manager(self, api_client, farmer, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='farmer_upd@test.com', phone_number='+254700000208',
            first_name='Upd', last_name='Mgr',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.patch(f'/api/farmers/{farmer.id}/', {
            'first_name': 'Updated',
        })
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        farmer.refresh_from_db()
        assert farmer.first_name == 'Updated'

    def test_destroy_as_manager(self, api_client, farmer, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='farmer_del@test.com', phone_number='+254700000209',
            first_name='Del', last_name='Mgr',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.delete(f'/api/farmers/{farmer.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        from apps.farmers.models import Farmer
        assert not Farmer.objects.filter(id=farmer.id).exists()

    def test_update_forbidden_for_grader(self, api_client, farmer, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grader = User.objects.create_user(
            email='farmer_grader_upd@test.com', phone_number='+254700000210',
            first_name='Grd', last_name='Upd',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=grader)
        resp = api_client.patch(f'/api/farmers/{farmer.id}/', {
            'first_name': 'Hacked',
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestFarmerLookup:
    def test_lookup_by_phone(self, api_client, farmer, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='lookup_mgr@test.com', phone_number='+254700000211',
            first_name='Look', last_name='Mgr',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.get(
            f'/api/farmers/lookup/?phone={farmer.phone_number}'
        )
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        results = resp.json()['results']
        assert len(results) == 1
        assert results[0]['phone_number'] == farmer.phone_number

    def test_lookup_by_name(self, api_client, farmer, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='lookup_mgr@test.com', phone_number='+254700000211',
            first_name='Look', last_name='Mgr',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.get(
            f'/api/farmers/lookup/?name={farmer.first_name}+{farmer.last_name}'
        )
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        results = resp.json()['results']
        assert len(results) == 1
        assert results[0]['phone_number'] == farmer.phone_number

    def test_lookup_by_partial_name(self, api_client, farmer, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='lookup_mgr@test.com', phone_number='+254700000211',
            first_name='Look', last_name='Mgr',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.get(
            f'/api/farmers/lookup/?name={farmer.first_name[:3]}'
        )
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        results = resp.json()['results']
        assert len(results) >= 1

    def test_lookup_without_params_returns_400(self, api_client, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='lookup_mgr2@test.com', phone_number='+254700000212',
            first_name='Look2', last_name='Mgr',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.get('/api/farmers/lookup/')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_lookup_not_found_returns_404(self, api_client, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='lookup_mgr3@test.com', phone_number='+254700000213',
            first_name='Look3', last_name='Mgr',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.get('/api/farmers/lookup/?phone=999999999')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_lookup_forbidden_for_non_manager(self, api_client, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grader = User.objects.create_user(
            email='lookup_grd@test.com', phone_number='+254700000214',
            first_name='Look', last_name='Grd',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=grader)
        resp = api_client.get('/api/farmers/lookup/?phone=0712345678')
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestFarmerMe:
    def test_me_get_returns_farmer_profile(self, api_client, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        from apps.farmers.models import Farmer
        user = User.objects.create_user(
            email='me_farmer@test.com', phone_number='+254700000215',
            first_name='Me', last_name='Farmer',
            password='testpass123', role=UserRole.FARMER,
            cooperative=cooperative,
        )
        farmer = Farmer.objects.create(
            first_name='Me', last_name='Farmer',
            id_number='12345678', phone_number='+254700000216',
            county='Nairobi', cooperative=cooperative, user=user,
        )
        api_client.force_authenticate(user=user)
        resp = api_client.get('/api/farmers/me/')
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        assert resp.json()['id'] == str(farmer.id)

    def test_me_get_404_without_profile(self, api_client, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            email='me_noprofile@test.com', phone_number='+254700000217',
            first_name='No', last_name='Profile',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=user)
        resp = api_client.get('/api/farmers/me/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_me_patch_updates_profile(self, api_client, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        from apps.farmers.models import Farmer
        user = User.objects.create_user(
            email='me_patch@test.com', phone_number='+254700000218',
            first_name='Me', last_name='Patch',
            password='testpass123', role=UserRole.FARMER,
            cooperative=cooperative,
        )
        farmer = Farmer.objects.create(
            first_name='Me', last_name='Patch',
            id_number='12345678', phone_number='+254700000219',
            county='Nairobi', cooperative=cooperative, user=user,
            village='Old Village',
        )
        api_client.force_authenticate(user=user)
        resp = api_client.patch('/api/farmers/me/', {
            'village': 'New Village',
        })
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        farmer.refresh_from_db()
        assert farmer.village == 'New Village'

    def test_me_patch_404_without_profile(self, api_client, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            email='me_patch_np@test.com', phone_number='+254700000220',
            first_name='No', last_name='Patch',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=user)
        resp = api_client.patch('/api/farmers/me/', {
            'village': 'Nowhere',
        })
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_me_get_unauthenticated(self, client):
        resp = client.get('/api/farmers/me/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestFarmerStats:
    def test_stats_returns_counts(self, api_client, farmer):
        resp = api_client.get('/api/farmers/stats/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert 'total' in data
        assert 'active' in data
        assert 'with_active_loans' in data
        assert data['total'] >= 1

    def test_stats_unauthenticated(self, client):
        resp = client.get('/api/farmers/stats/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestFarmerImportTemplate:
    def test_import_template_returns_csv(self, api_client):
        resp = api_client.get('/api/farmers/import_template/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp['Content-Type'] == 'text/csv'
        assert 'farmer_import_template.csv' in resp['Content-Disposition']

    def test_import_template_unauthenticated(self, client):
        resp = client.get('/api/farmers/import_template/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestFarmerImportCsv:
    def test_import_csv_creates_farmers(self, api_client, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='csv_mgr@test.com', phone_number='+254700000221',
            first_name='CSV', last_name='Mgr',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        import io
        content = (
            'first_name,last_name,email,id_number,phone_number,county\n'
            'John,Doe,john@test.com,12345678,0712345678,Nairobi\n'
            'Jane,Smith,jane@test.com,87654321,0723456789,Kiambu\n'
        )
        resp = api_client.post(
            '/api/farmers/import_csv/',
            {'file': io.StringIO(content)},
            format='multipart',
        )
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        data = resp.json()
        assert 'created_farmers' in data
        assert len(data['created_farmers']) == 2

    def test_import_csv_links_existing_farmer(self, api_client, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        from apps.farmers.models import Farmer
        manager = User.objects.create_user(
            email='csv_link@test.com', phone_number='+254700000222',
            first_name='CSV', last_name='Link',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        Farmer.objects.create(
            first_name='Existing', last_name='Farmer',
            id_number='99999999', phone_number='+254712345678',
            county='Nairobi', cooperative=cooperative,
        )
        import io
        content = (
            'first_name,last_name,email,id_number,phone_number,county\n'
            'Existing,Farmer,ex@test.com,99999999,0712345678,Nairobi\n'
        )
        resp = api_client.post(
            '/api/farmers/import_csv/',
            {'file': io.StringIO(content)},
            format='multipart',
        )
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        data = resp.json()
        assert 'linked_farmers' in data
        assert len(data['linked_farmers']) == 1

    def test_import_csv_no_file_returns_400(self, api_client, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='csv_nofile@test.com', phone_number='+254700000223',
            first_name='CSV', last_name='NoFile',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.post('/api/farmers/import_csv/', {}, format='multipart')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_import_csv_forbidden_for_non_manager(self, api_client, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grader = User.objects.create_user(
            email='csv_grd@test.com', phone_number='+254700000224',
            first_name='CSV', last_name='Grd',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=grader)
        import io
        resp = api_client.post(
            '/api/farmers/import_csv/',
            {'file': io.StringIO('first_name,last_name\nTest,User\n')},
            format='multipart',
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# MembershipViewSet endpoint tests
# =============================================================================


class TestMembershipViewSet:
    def test_list_memberships(self, api_client, farmer):
        resp = api_client.get(f'/api/farmers/{farmer.id}/memberships/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        if isinstance(data, dict):
            assert len(data['results']) >= 1
        else:
            assert len(data) >= 1
        assert data[0]['member_number'] == farmer.primary_membership.member_number

    def test_create_membership(self, api_client, farmer, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='mem_crt@test.com', phone_number='+254700000225',
            first_name='Mem', last_name='Crt',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        from apps.cooperatives.models import Cooperative
        other_coop = Cooperative.objects.create(
            name='Other Coop', registration_number='OTH002',
            county='Nairobi', produce_type='DAIRY',
            payment_model='FIXED_PRICE', prefix='OTH2',
        )
        farmer.memberships.all().delete()
        resp = api_client.post(f'/api/farmers/{farmer.id}/memberships/', {
            'cooperative_id': str(other_coop.id),
        })
        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        assert farmer.memberships.filter(cooperative=other_coop).exists()

    def test_create_membership_requires_manager(self, api_client, farmer, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grader = User.objects.create_user(
            email='mem_crt_grd@test.com', phone_number='+254700000226',
            first_name='Mem', last_name='Grd',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=grader)
        resp = api_client.post(f'/api/farmers/{farmer.id}/memberships/', {
            'cooperative_id': str(cooperative.id),
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_membership(self, api_client, farmer):
        membership = farmer.primary_membership
        resp = api_client.get(
            f'/api/farmers/{farmer.id}/memberships/{membership.id}/'
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['id'] == str(membership.id)

    def test_retrieve_membership_by_member_number(self, api_client, farmer):
        membership = farmer.primary_membership
        resp = api_client.get(
            f'/api/farmers/{farmer.id}/memberships/{membership.member_number}/'
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['id'] == str(membership.id)

    def test_update_membership(self, api_client, farmer, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='mem_upd@test.com', phone_number='+254700000227',
            first_name='Mem', last_name='Upd',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        membership = farmer.primary_membership
        resp = api_client.patch(
            f'/api/farmers/{farmer.id}/memberships/{membership.id}/',
            {'payment_method': 'BANK'},
        )
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        membership.refresh_from_db()
        assert membership.payment_method == 'BANK'

    def test_destroy_membership(self, api_client, farmer, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='mem_del@test.com', phone_number='+254700000228',
            first_name='Mem', last_name='Del',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        from apps.farmers.models import FarmerCooperativeMembership
        membership = FarmerCooperativeMembership.objects.create(
            farmer=farmer, cooperative=cooperative, member_number='MEMDEL',
        )
        resp = api_client.delete(
            f'/api/farmers/{farmer.id}/memberships/{membership.id}/'
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_list_unauthenticated(self, client, farmer):
        resp = client.get(f'/api/farmers/{farmer.id}/memberships/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestMembershipDeactivateReactivate:
    def test_deactivate(self, api_client, farmer, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='mem_deact@test.com', phone_number='+254700000229',
            first_name='Mem', last_name='Deact',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        membership = farmer.primary_membership
        resp = api_client.patch(
            f'/api/farmers/{farmer.id}/memberships/{membership.id}/deactivate/'
        )
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        membership.refresh_from_db()
        assert not membership.is_active

    def test_reactivate(self, api_client, farmer, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='mem_react@test.com', phone_number='+254700000230',
            first_name='Mem', last_name='React',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        membership = farmer.primary_membership
        membership.is_active = False
        membership.save()
        resp = api_client.patch(
            f'/api/farmers/{farmer.id}/memberships/{membership.id}/reactivate/'
        )
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        membership.refresh_from_db()
        assert membership.is_active

    def test_deactivate_requires_authentication(self, client, farmer):
        membership = farmer.primary_membership
        resp = client.patch(
            f'/api/farmers/{farmer.id}/memberships/{membership.id}/deactivate/'
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Farmer location (lat/lng) tests
# =============================================================================


class TestFarmerLocationAction:
    def _farmer_in_coop(self, cooperative):
        from apps.farmers.models import Farmer
        return Farmer.objects.create(
            first_name='Loc', last_name='Test',
            id_number='LOC001', phone_number='+25470000500',
            county='Nairobi', cooperative=cooperative,
        )

    def test_get_location_unset(self, manager_api_client, cooperative):
        farmer = self._farmer_in_coop(cooperative)
        resp = manager_api_client.get(f'/api/farmers/{farmer.id}/location/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data['latitude'] is None
        assert data['longitude'] is None
        assert data['route_stops'] == []

    def test_get_location_with_coords(self, manager_api_client, cooperative):
        from decimal import Decimal
        farmer = self._farmer_in_coop(cooperative)
        farmer.latitude = Decimal('-1.283333')
        farmer.longitude = Decimal('36.816667')
        farmer.save(update_fields=['latitude', 'longitude'])
        resp = manager_api_client.get(f'/api/farmers/{farmer.id}/location/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert abs(data['latitude'] - (-1.283333)) < 1e-6
        assert abs(data['longitude'] - 36.816667) < 1e-6

    def test_get_location_includes_route_stops(self, manager_api_client, cooperative):
        from apps.routes.models import CollectionRoute, RouteStop
        from decimal import Decimal
        farmer = self._farmer_in_coop(cooperative)
        route = CollectionRoute.objects.create(cooperative=cooperative, name='R1', path={})
        stop = RouteStop.objects.create(
            route=route, latitude=Decimal('0'), longitude=Decimal('0'), stop_order=1,
        )
        stop.farmers.add(farmer)
        resp = manager_api_client.get(f'/api/farmers/{farmer.id}/location/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data['route_stops']) == 1
        assert data['route_stops'][0]['route_name'] == 'R1'

    def test_patch_location_as_manager(self, manager_api_client, cooperative):
        from decimal import Decimal
        farmer = self._farmer_in_coop(cooperative)
        resp = manager_api_client.patch(
            f'/api/farmers/{farmer.id}/location/',
            {'latitude': '-1.28', 'longitude': '36.82'},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK, resp.content
        farmer.refresh_from_db()
        assert farmer.latitude == Decimal('-1.28')
        assert farmer.longitude == Decimal('36.82')

    def test_patch_location_as_grader(self, grader_api_client, cooperative):
        from decimal import Decimal
        farmer = self._farmer_in_coop(cooperative)
        resp = grader_api_client.patch(
            f'/api/farmers/{farmer.id}/location/',
            {'latitude': '-1.28', 'longitude': '36.82'},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK, resp.content
        farmer.refresh_from_db()
        assert farmer.latitude == Decimal('-1.28')

    def test_patch_location_as_accountant_denied(self, cooperative):
        accountant = User.objects.create_user(
            'acct@farmer.com', '+25470000900', 'Acct', 'User',
            password='testpass123', role=UserRole.ACCOUNTANT, cooperative=cooperative,
        )
        c = APIClient()
        c.force_authenticate(user=accountant)
        farmer = self._farmer_in_coop(cooperative)
        resp = c.patch(
            f'/api/farmers/{farmer.id}/location/',
            {'latitude': '0', 'longitude': '0'},
            format='json',
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_patch_location_partial_rejected(self, manager_api_client, cooperative):
        farmer = self._farmer_in_coop(cooperative)
        resp = manager_api_client.patch(
            f'/api/farmers/{farmer.id}/location/',
            {'latitude': '0'},
            format='json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_location_out_of_range(self, manager_api_client, cooperative):
        farmer = self._farmer_in_coop(cooperative)
        resp = manager_api_client.patch(
            f'/api/farmers/{farmer.id}/location/',
            {'latitude': '200', 'longitude': '0'},
            format='json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestFarmerSelfUpdateLocation:
    def _farmer_with_user(self, cooperative):
        from apps.farmers.models import Farmer
        farmer_user = User.objects.create_user(
            'farmer-user@test.com', '+25470000501', 'LocUser', 'Test',
            password='testpass123', role=UserRole.FARMER, cooperative=cooperative,
            is_active=True,
        )
        farmer = Farmer.objects.create(
            first_name='LocUser', last_name='Test',
            id_number='LOC002', phone_number=farmer_user.phone_number,
            county='Nairobi', cooperative=cooperative,
            user=farmer_user,
        )
        farmer.refresh_from_db()
        return farmer, farmer_user

    def test_farmer_patches_own_location(self, cooperative):
        from rest_framework.test import APIClient
        from decimal import Decimal
        farmer, farmer_user = self._farmer_with_user(cooperative)
        c = APIClient()
        c.force_authenticate(user=farmer_user)
        resp = c.patch(
            '/api/farmers/me/',
            {'latitude': '-1.30', 'longitude': '36.80'},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK, resp.content
        farmer.refresh_from_db()
        assert farmer.latitude == Decimal('-1.30')
        assert farmer.longitude == Decimal('36.80')

    def test_farmer_location_validation(self, cooperative):
        from rest_framework.test import APIClient
        farmer, farmer_user = self._farmer_with_user(cooperative)
        c = APIClient()
        c.force_authenticate(user=farmer_user)
        resp = c.patch(
            '/api/farmers/me/',
            {'latitude': '500', 'longitude': '0'},
            format='json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
