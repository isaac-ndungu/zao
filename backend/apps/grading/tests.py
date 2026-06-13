from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

pytestmark = pytest.mark.django_db

from apps.grading.models import (
    DisputeStatus,
    FarmerGradeDispute,
    Grade,
    GradeImage,
    GradeLetter,
    GradePrice,
)


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
