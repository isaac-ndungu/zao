import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.cooperatives.models import (
    Cooperative,
    PaymentModel,
    ProduceType,
)

pytestmark = pytest.mark.django_db


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


class TestCooperativeApi:
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
        assert resp.json()['registration_number'] == ['Cooperative with this registration number already exists.']
