from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status

pytestmark = pytest.mark.django_db

from apps.base.constants import UserRole
from apps.grading.models import (
    DisputeStatus,
    FarmerGradeDispute,
    Grade,
    GradeImage,
    GradeLetter,
    GradePrice,
)


# =============================================================================
# Model tests (kept from original)
# =============================================================================


class TestGradeModel:
    def test_create(self, delivery):
        grade = Grade.objects.create(
            delivery=delivery,
            cooperative=delivery.cooperative,
            grade_letter=GradeLetter.A,
            price_per_unit=Decimal('45.00'),
        )
        assert grade.pk is not None

    def test_one_to_one_with_delivery(self, delivery):
        Grade.objects.create(
            delivery=delivery,
            cooperative=delivery.cooperative,
            grade_letter=GradeLetter.A,
        )
        with pytest.raises(Exception):
            Grade.objects.create(
                delivery=delivery,
                cooperative=delivery.cooperative,
                grade_letter=GradeLetter.B,
            )

    def test_str_with_grade(self, delivery):
        grade = Grade.objects.create(
            delivery=delivery,
            cooperative=delivery.cooperative,
            grade_letter=GradeLetter.PREMIUM,
            price_per_unit=Decimal('50.00'),
        )
        assert str(delivery.batch_id) in str(grade)
        assert 'PREMIUM' in str(grade)

    def test_str_rejected(self, delivery):
        grade = Grade.objects.create(
            delivery=delivery,
            cooperative=delivery.cooperative,
            grade_letter='',
            rejection_reason='Poor quality',
        )
        assert 'REJECTED' in str(grade)

    def test_default_not_overridden(self, delivery):
        grade = Grade.objects.create(
            delivery=delivery,
            cooperative=delivery.cooperative,
        )
        assert not grade.is_overridden

    def test_m2m_images(self, delivery):
        grade = Grade.objects.create(
            delivery=delivery,
            cooperative=delivery.cooperative,
        )
        img = GradeImage.objects.create(caption='Test image')
        grade.images.add(img)
        assert grade.images.count() == 1

    def test_soft_delete(self, delivery):
        grade = Grade.objects.create(
            delivery=delivery,
            cooperative=delivery.cooperative,
        )
        grade.soft_delete()
        assert grade.deleted_at is not None


class TestGradePrice:
    def test_create(self):
        gp = GradePrice.objects.create(
            grade_letter=GradeLetter.A,
            price_per_unit=Decimal('45.00'),
            effective_from='2024-01-01',
        )
        assert gp.pk is not None

    def test_unique_together(self):
        GradePrice.objects.create(
            grade_letter=GradeLetter.A,
            price_per_unit=Decimal('45.00'),
            effective_from='2024-01-01',
        )
        with pytest.raises(Exception):
            GradePrice.objects.create(
                grade_letter=GradeLetter.A,
                price_per_unit=Decimal('50.00'),
                effective_from='2024-01-01',
            )

    def test_str(self):
        gp = GradePrice.objects.create(
            grade_letter=GradeLetter.B,
            price_per_unit=Decimal('40.00'),
            effective_from='2024-06-01',
        )
        assert 'B' in str(gp)
        assert '40.00' in str(gp)


class TestGradeImage:
    def test_create(self):
        img = GradeImage.objects.create(caption='Quality check')
        assert img.pk is not None

    def test_str(self):
        img = GradeImage.objects.create()
        assert 'GradeImage' in str(img)


class TestFarmerGradeDispute:
    def test_create(self, grade, superuser):
        dispute = FarmerGradeDispute.objects.create(
            grade=grade,
            raised_by=superuser,
            reason='Wrong grade assigned',
        )
        assert dispute.pk is not None
        assert dispute.status == DisputeStatus.PENDING

    def test_resolve(self, grade, superuser):
        dispute = FarmerGradeDispute.objects.create(
            grade=grade,
            raised_by=superuser,
            reason='Test dispute',
        )
        dispute.status = DisputeStatus.RESOLVED
        dispute.resolved_by = superuser
        dispute.resolution_notes = 'Grade corrected'
        dispute.save()
        dispute.refresh_from_db()
        assert dispute.status == DisputeStatus.RESOLVED

    def test_str(self, grade, superuser):
        dispute = FarmerGradeDispute.objects.create(
            grade=grade,
            raised_by=superuser,
            reason='Dispute reason',
        )
        assert str(grade) in str(dispute)
        assert DisputeStatus.PENDING in str(dispute)


# =============================================================================
# GradeViewSet endpoint tests
# =============================================================================


def _make_coop_delivery(cooperative):
    """Create a delivery scoped to a specific cooperative."""
    from apps.farmers.models import Farmer
    from apps.deliveries.models import Delivery
    farmer = Farmer.objects.create(
        first_name='Grade', last_name='Test',
        id_number='IDGRADE01', phone_number='+254790000001',
        county='Nairobi', cooperative=cooperative,
    )
    return Delivery.objects.create(
        farmer=farmer, cooperative=cooperative,
        product_type='MILK', quantity_kg=Decimal('100.00'),
        status='PENDING', date_delivered=timezone.now(),
        batch_id=f"GDTEST-{str(cooperative.id)[:8]}",
    )


class TestGradeViewSetList:
    def test_list_as_admin(self, api_client, grade):
        resp = api_client.get('/api/grades/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        if isinstance(data, dict):
            assert len(data['results']) >= 1
        else:
            assert len(data) >= 1

    def test_list_filters_by_grade_letter(self, api_client, grade):
        resp = api_client.get(f'/api/grades/?grade_letter={grade.grade_letter}')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        items = data['results'] if isinstance(data, dict) else data
        for item in items:
            assert item['grade_letter'] == grade.grade_letter

    def test_list_filters_by_delivery(self, api_client, grade):
        resp = api_client.get(f'/api/grades/?delivery={grade.delivery_id}')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        items = data['results'] if isinstance(data, dict) else data
        assert len(items) == 1
        assert items[0]['delivery'] == str(grade.delivery_id)

    def test_list_farmer_sees_only_own_grades(self, api_client, cooperative, delivery):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        farmer_user = User.objects.create_user(
            email='gradingfarmer@test.com', phone_number='+254799999991',
            first_name='Farmer', last_name='Grader',
            password='testpass123', role=UserRole.FARMER,
            cooperative=cooperative,
        )
        delivery.farmer.user = farmer_user
        delivery.farmer.save()
        api_client.force_authenticate(user=farmer_user)
        resp = api_client.get('/api/grades/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        items = data['results'] if isinstance(data, dict) else data
        assert len(items) == 1
        assert items[0]['id'] == str(grade.id)

    def test_list_other_farmer_excluded(self, api_client, cooperative, grade):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        other_farmer = User.objects.create_user(
            email='otherfarmer@test.com', phone_number='+254799999992',
            first_name='Other', last_name='Farmer',
            password='testpass123', role=UserRole.FARMER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=other_farmer)
        resp = api_client.get('/api/grades/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        items = data['results'] if isinstance(data, dict) else data
        assert len(items) == 0

    def test_list_unauthenticated(self, client):
        resp = client.get('/api/grades/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestGradeViewSetCreate:
    def test_create_grade_as_grader(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grader = User.objects.create_user(
            email='grader_create@test.com', phone_number='+254700000101',
            first_name='Grader', last_name='Create',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=grader)
        resp = api_client.post('/api/grades/', {
            'delivery': delivery.id,
            'grade_letter': 'A',
            'price_per_unit': '45.00',
        })
        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        assert resp.json()['grade_letter'] == 'A'

    def test_create_grade_rejected(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grader = User.objects.create_user(
            email='grader_rej@test.com', phone_number='+254700000102',
            first_name='Grader', last_name='Rej',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=grader)
        resp = api_client.post('/api/grades/', {
            'delivery': delivery.id,
            'rejection_reason': 'Poor quality',
        })
        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        grade = Grade.objects.get(id=resp.json()['id'])
        assert grade.rejection_reason == 'Poor quality'

    def test_create_sets_delivery_graded(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grader = User.objects.create_user(
            email='grader_del@test.com', phone_number='+254700000103',
            first_name='Grader', last_name='Del',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=grader)
        resp = api_client.post('/api/grades/', {
            'delivery': delivery.id,
            'grade_letter': 'B',
            'price_per_unit': '40.00',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        delivery.refresh_from_db()
        assert delivery.status == 'GRADED'
        assert delivery.grade == 'B'
        assert delivery.rejection_reason == ''

    def test_create_sets_delivery_rejected(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grader = User.objects.create_user(
            email='grader_delr@test.com', phone_number='+254700000104',
            first_name='Grader', last_name='DelR',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=grader)
        resp = api_client.post('/api/grades/', {
            'delivery': delivery.id,
            'rejection_reason': 'Contaminated',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        delivery.refresh_from_db()
        assert delivery.status == 'REJECTED'
        assert delivery.rejection_reason == 'Contaminated'

    def test_create_forbidden_without_grader_role(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='mgr_no_grade@test.com', phone_number='+254700000105',
            first_name='Manager', last_name='NoGrade',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.post('/api/grades/', {
            'delivery': delivery.id,
            'grade_letter': 'A',
            'price_per_unit': '45.00',
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_create_unauthenticated(self, client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        resp = client.post('/api/grades/', {
            'delivery': delivery.id,
            'grade_letter': 'A',
            'price_per_unit': '45.00',
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_validates_grade_and_rejection_mutual_exclusion(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grader = User.objects.create_user(
            email='grader_val@test.com', phone_number='+254700000106',
            first_name='Grader', last_name='Val',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=grader)
        resp = api_client.post('/api/grades/', {
            'delivery': delivery.id,
            'grade_letter': 'A',
            'rejection_reason': 'Bad quality',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_requires_price_with_grade(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grader = User.objects.create_user(
            email='grader_price@test.com', phone_number='+254700000107',
            first_name='Grader', last_name='PriceReq',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=grader)
        resp = api_client.post('/api/grades/', {
            'delivery': delivery.id,
            'grade_letter': 'A',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestGradeViewSetRetrieveUpdateDestroy:
    def test_retrieve(self, api_client, grade):
        resp = api_client.get(f'/api/grades/{grade.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['id'] == str(grade.id)

    def test_retrieve_unauthenticated(self, client, grade):
        resp = client.get(f'/api/grades/{grade.id}/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_as_manager(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        manager = User.objects.create_user(
            email='mgr_update@test.com', phone_number='+254700000108',
            first_name='Manager', last_name='Upd',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.patch(f'/api/grades/{grade.id}/', {
            'grade_letter': 'PREMIUM', 'price_per_unit': '50.00',
        })
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        grade.refresh_from_db()
        assert grade.grade_letter == 'PREMIUM'

    def test_update_as_grader(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='B', price_per_unit=Decimal('40.00'),
        )
        grader = User.objects.create_user(
            email='grader_upd@test.com', phone_number='+254700000109',
            first_name='Grader', last_name='Upd',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=grader)
        resp = api_client.patch(f'/api/grades/{grade.id}/', {
            'rejection_reason': 'Updated reason',
        })
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        grade.refresh_from_db()
        assert grade.rejection_reason == 'Updated reason'

    def test_update_forbidden_as_farmer(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        farmer_user = User.objects.create_user(
            email='farmer_upd@test.com', phone_number='+254700000110',
            first_name='Farmer', last_name='Upd',
            password='testpass123', role=UserRole.FARMER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=farmer_user)
        resp = api_client.patch(f'/api/grades/{grade.id}/', {
            'grade_letter': 'A',
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_destroy_as_manager(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        manager = User.objects.create_user(
            email='mgr_del@test.com', phone_number='+254700000111',
            first_name='Manager', last_name='Del',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.delete(f'/api/grades/{grade.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Grade.objects.filter(id=grade.id).exists()

    def test_destroy_as_grader(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='B', price_per_unit=Decimal('40.00'),
        )
        grader = User.objects.create_user(
            email='grader_del@test.com', phone_number='+254700000112',
            first_name='Grader', last_name='Del',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=grader)
        resp = api_client.delete(f'/api/grades/{grade.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_destroy_forbidden_as_farmer(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        farmer_user = User.objects.create_user(
            email='farmer_del@test.com', phone_number='+254700000113',
            first_name='Farmer', last_name='Del',
            password='testpass123', role=UserRole.FARMER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=farmer_user)
        resp = api_client.delete(f'/api/grades/{grade.id}/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestGradeViewSetOverride:
    def test_override_post_as_manager(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='mgr_ovr@test.com', phone_number='+254700000114',
            first_name='Mgr', last_name='Ovr',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.post(f'/api/grades/{grade.id}/override/', {
            'grade_letter': 'PREMIUM',
            'price_per_unit': '55.00',
            'override_reason': 'Exceptional quality',
        })
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        grade.refresh_from_db()
        assert grade.is_overridden
        assert grade.grade_letter == 'PREMIUM'
        assert grade.overridden_by == manager
        assert grade.overridden_at is not None

    def test_override_patch_as_manager(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='mgr_ovrp@test.com', phone_number='+254700000115',
            first_name='Mgr', last_name='OvrP',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.patch(f'/api/grades/{grade.id}/override/', {
            'grade_letter': 'A',
            'price_per_unit': '45.00',
            'override_reason': 'Correcting grade',
        })
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        grade.refresh_from_db()
        assert grade.is_overridden
        assert grade.grade_letter == 'A'

    def test_override_forbidden_for_grader(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grader = User.objects.create_user(
            email='grader_ovr@test.com', phone_number='+254700000116',
            first_name='Grader', last_name='Ovr',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=grader)
        resp = api_client.post(f'/api/grades/{grade.id}/override/', {
            'grade_letter': 'PREMIUM',
            'price_per_unit': '55.00',
            'override_reason': 'Test',
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_override_requires_reason(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='mgr_ovr_nr@test.com', phone_number='+254700000117',
            first_name='Mgr', last_name='NoReason',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.post(f'/api/grades/{grade.id}/override/', {
            'grade_letter': 'PREMIUM',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestGradeViewSetPrices:
    def test_prices_get(self, api_client, cooperative):
        GradePrice.objects.create(
            grade_letter='A', price_per_unit=Decimal('45.00'),
            effective_from='2024-01-01',
        )
        GradePrice.objects.create(
            grade_letter='B', price_per_unit=Decimal('40.00'),
            effective_from='2024-01-01',
        )
        resp = api_client.get('/api/grades/prices/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        items = data['results'] if isinstance(data, dict) else data
        assert len(items) >= 2

    def test_prices_get_unauthenticated(self, client):
        resp = client.get('/api/grades/prices/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_prices_post_as_admin(self, api_client):
        resp = api_client.post('/api/grades/prices/', {
            'grade_letter': 'PREMIUM',
            'price_per_unit': '50.00',
            'effective_from': '2024-07-01',
        })
        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        assert GradePrice.objects.filter(grade_letter='PREMIUM').exists()

    def test_prices_post_forbidden_for_manager(self, api_client, cooperative):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='mgr_price@test.com', phone_number='+254700000118',
            first_name='Mgr', last_name='Price',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.post('/api/grades/prices/', {
            'grade_letter': 'PREMIUM',
            'price_per_unit': '50.00',
            'effective_from': '2024-07-01',
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestGradeViewSetDispute:
    def test_dispute_post_as_farmer(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        farmer_user = User.objects.create_user(
            email='dispute_farmer@test.com', phone_number='+254700000119',
            first_name='Dispute', last_name='Farmer',
            password='testpass123', role=UserRole.FARMER,
            cooperative=cooperative,
        )
        delivery.farmer.user = farmer_user
        delivery.farmer.save()
        api_client.force_authenticate(user=farmer_user)
        resp = api_client.post(f'/api/grades/{grade.id}/dispute/', {
            'reason': 'Wrong grade assigned',
        })
        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        assert FarmerGradeDispute.objects.filter(
            grade=grade, raised_by=farmer_user
        ).exists()

    def test_dispute_forbidden_for_non_farmer(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='mgr_dispute@test.com', phone_number='+254700000120',
            first_name='Mgr', last_name='Dispute',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.post(f'/api/grades/{grade.id}/dispute/', {
            'reason': 'Test dispute',
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_dispute_forbidden_for_other_farmers_grade(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        from apps.farmers.models import Farmer
        other_farmer = Farmer.objects.create(
            first_name='Other', last_name='Farmer',
            id_number='ID999999', phone_number='+254700000121',
            county='Nairobi', cooperative=cooperative,
        )
        other_user = User.objects.create_user(
            email='other_dispute@test.com', phone_number='+254700000122',
            first_name='Other', last_name='Dispute',
            password='testpass123', role=UserRole.FARMER,
            cooperative=cooperative,
        )
        other_farmer.user = other_user
        other_farmer.save()
        api_client.force_authenticate(user=other_user)
        resp = api_client.post(f'/api/grades/{grade.id}/dispute/', {
            'reason': 'Not my grade but disputing',
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestGradeViewSetImages:
    def test_images_get(self, api_client, grade):
        img = GradeImage.objects.create(caption='Test')
        grade.images.add(img)
        resp = api_client.get(f'/api/grades/{grade.id}/images/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) == 1
        assert data[0]['caption'] == 'Test'

    def test_images_get_unauthenticated(self, client, grade):
        resp = client.get(f'/api/grades/{grade.id}/images/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_images_post_as_grader(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grader = User.objects.create_user(
            email='img_grader@test.com', phone_number='+254700000123',
            first_name='Img', last_name='Grader',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=grader)
        from io import BytesIO
        from PIL import Image as PILImage
        img_file = BytesIO()
        PILImage.new('RGB', (800, 600)).save(img_file, 'JPEG')
        img_file.seek(0)
        img_file.name = 'test.jpg'
        resp = api_client.post(
            f'/api/grades/{grade.id}/images/',
            {'image': img_file, 'caption': 'Quality check'},
            format='multipart',
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        assert grade.images.count() == 1

    def test_images_post_forbidden_for_non_grader(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='img_mgr@test.com', phone_number='+254700000124',
            first_name='Img', last_name='Mgr',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        from io import BytesIO
        from PIL import Image as PILImage
        img_file = BytesIO()
        PILImage.new('RGB', (800, 600)).save(img_file, 'JPEG')
        img_file.seek(0)
        img_file.name = 'test.jpg'
        resp = api_client.post(
            f'/api/grades/{grade.id}/images/',
            {'image': img_file, 'caption': 'Quality check'},
            format='multipart',
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_image_by_uploader(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grader = User.objects.create_user(
            email='img_del@test.com', phone_number='+254700000125',
            first_name='Img', last_name='Del',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=grader)
        img = GradeImage.objects.create(caption='To delete', uploaded_by=grader)
        grade.images.add(img)
        resp = api_client.delete(f'/api/grades/{grade.id}/images/{img.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert grade.images.count() == 0

    def test_delete_image_by_manager(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grader = User.objects.create_user(
            email='img_del_g@test.com', phone_number='+254700000126',
            first_name='Img', last_name='DelG',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        manager = User.objects.create_user(
            email='img_del_m@test.com', phone_number='+254700000127',
            first_name='Img', last_name='DelM',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        img = GradeImage.objects.create(caption='Managed', uploaded_by=grader)
        grade.images.add(img)
        api_client.force_authenticate(user=manager)
        resp = api_client.delete(f'/api/grades/{grade.id}/images/{img.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_image_forbidden_for_other_user(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grader = User.objects.create_user(
            email='img_del_o1@test.com', phone_number='+254700000128',
            first_name='Img', last_name='DelO1',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        other_grader = User.objects.create_user(
            email='img_del_o2@test.com', phone_number='+254700000129',
            first_name='Img', last_name='DelO2',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        img = GradeImage.objects.create(caption='Other', uploaded_by=grader)
        grade.images.add(img)
        api_client.force_authenticate(user=other_grader)
        resp = api_client.delete(f'/api/grades/{grade.id}/images/{img.id}/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_image_not_on_grade(self, api_client, cooperative):
        delivery = _make_coop_delivery(cooperative)
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='img_del_nf@test.com', phone_number='+254700000130',
            first_name='Img', last_name='NF',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        api_client.force_authenticate(user=manager)
        img = GradeImage.objects.create(caption='Orphan')
        resp = api_client.delete(f'/api/grades/{grade.id}/images/{img.id}/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# GradeDisputeViewSet endpoint tests
# =============================================================================


class TestGradeDisputeViewSet:
    def test_list(self, api_client, grade, superuser):
        FarmerGradeDispute.objects.create(
            grade=grade, raised_by=superuser, reason='Test'
        )
        resp = api_client.get('/api/disputes/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        if isinstance(data, dict):
            assert len(data['results']) >= 1
        else:
            assert len(data) >= 1

    def test_create(self, api_client, grade, superuser):
        resp = api_client.post('/api/disputes/', {
            'grade': grade.id,
            'reason': 'Wrong grade',
        })
        assert resp.status_code == status.HTTP_201_CREATED, resp.json()
        assert resp.json()['reason'] == 'Wrong grade'

    def test_retrieve(self, api_client, grade, superuser):
        dispute = FarmerGradeDispute.objects.create(
            grade=grade, raised_by=superuser, reason='Test'
        )
        resp = api_client.get(f'/api/disputes/{dispute.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['id'] == str(dispute.id)

    def test_update(self, api_client, grade, superuser):
        dispute = FarmerGradeDispute.objects.create(
            grade=grade, raised_by=superuser, reason='Initial'
        )
        resp = api_client.patch(f'/api/disputes/{dispute.id}/', {
            'reason': 'Updated reason',
        })
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        dispute.refresh_from_db()
        assert dispute.reason == 'Updated reason'

    def test_destroy(self, api_client, grade, superuser):
        dispute = FarmerGradeDispute.objects.create(
            grade=grade, raised_by=superuser, reason='To delete'
        )
        resp = api_client.delete(f'/api/disputes/{dispute.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not FarmerGradeDispute.objects.filter(id=dispute.id).exists()


class TestGradeDisputeResolve:
    def test_resolve_post(self, api_client, cooperative, superuser):
        delivery = _make_coop_delivery(cooperative)
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='resolve_mgr@test.com', phone_number='+254700000131',
            first_name='Resolve', last_name='Mgr',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        dispute = FarmerGradeDispute.objects.create(
            grade=grade, raised_by=superuser, reason='Fix grade',
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.post(f'/api/disputes/{dispute.id}/resolve/', {
            'resolution': 'RESOLVED',
            'notes': 'Grade corrected to A',
        })
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        dispute.refresh_from_db()
        assert dispute.status == DisputeStatus.RESOLVED
        assert dispute.resolved_by == manager
        assert dispute.resolved_at is not None

    def test_resolve_patch(self, api_client, cooperative, superuser):
        delivery = _make_coop_delivery(cooperative)
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='resolve_mgr2@test.com', phone_number='+254700000132',
            first_name='Resolve', last_name='Mgr2',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        dispute = FarmerGradeDispute.objects.create(
            grade=grade, raised_by=superuser, reason='Test',
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.patch(f'/api/disputes/{dispute.id}/resolve/', {
            'resolution': 'REJECTED',
            'notes': 'No issue found',
        })
        assert resp.status_code == status.HTTP_200_OK, resp.json()
        dispute.refresh_from_db()
        assert dispute.status == DisputeStatus.REJECTED

    def test_resolve_forbidden_for_non_manager(self, api_client, cooperative, superuser):
        delivery = _make_coop_delivery(cooperative)
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        grader = User.objects.create_user(
            email='resolve_grader@test.com', phone_number='+254700000133',
            first_name='Resolve', last_name='Grader',
            password='testpass123', role=UserRole.GRADER,
            cooperative=cooperative,
        )
        dispute = FarmerGradeDispute.objects.create(
            grade=grade, raised_by=superuser, reason='Test',
        )
        api_client.force_authenticate(user=grader)
        resp = api_client.post(f'/api/disputes/{dispute.id}/resolve/', {
            'resolution': 'RESOLVED',
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_resolve_fails_if_not_pending(self, api_client, cooperative, superuser):
        delivery = _make_coop_delivery(cooperative)
        grade = Grade.objects.create(
            delivery=delivery, cooperative=cooperative,
            grade_letter='A', price_per_unit=Decimal('45.00'),
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        manager = User.objects.create_user(
            email='resolve_mgr3@test.com', phone_number='+254700000134',
            first_name='Resolve', last_name='Mgr3',
            password='testpass123', role=UserRole.MANAGER,
            cooperative=cooperative,
        )
        dispute = FarmerGradeDispute.objects.create(
            grade=grade, raised_by=superuser, reason='Test',
            status=DisputeStatus.RESOLVED,
        )
        api_client.force_authenticate(user=manager)
        resp = api_client.post(f'/api/disputes/{dispute.id}/resolve/', {
            'resolution': 'REJECTED',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
