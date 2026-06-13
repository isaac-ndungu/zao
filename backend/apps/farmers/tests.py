import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.farmers.models import Farmer, FarmerCooperativeMembership, FarmerPaymentMethod

pytestmark = pytest.mark.django_db


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
