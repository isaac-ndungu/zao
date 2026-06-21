"""
Smoke tests for the full payment flow: Delivery → Grade → Inventory → Sale → PaymentCycle → Disbursement.
Tests API endpoints end-to-end with minimal mocking.
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.base.constants import UserRole
from apps.deliveries.models import Delivery
from apps.grading.models import Grade
from apps.grading.tasks import update_inventory_on_grade
from apps.payment_engine.engine import compute_fixed_price
from apps.payment_engine.models import FarmerPayment, PaymentCycle
from apps.sales.models import Sale

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.api,
]


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    client.user = user
    return client


@pytest.fixture
def manager(cooperative, db):
    from apps.conftest import UserFactory
    return UserFactory(
        role=UserRole.MANAGER,
        cooperative=cooperative,
        is_superuser=True,
        is_staff=True,
    )


@pytest.fixture
def manager_client(manager):
    return _client(manager)


@pytest.fixture
def grader(cooperative, db):
    from apps.conftest import UserFactory
    return UserFactory(
        role=UserRole.GRADER,
        cooperative=cooperative,
        is_superuser=True,
        is_staff=True,
        email='grader@example.com',
        phone_number='+254799999999',
    )


@pytest.fixture
def grader_client(grader):
    return _client(grader)


def test_full_payment_flow(manager_client, grader_client, cooperative, buyer):
    from apps.conftest import FarmerFactory
    farmer = FarmerFactory(cooperative=cooperative)

    buyer.cooperative = cooperative
    buyer.save()

    from apps.grading.models import GradePrice
    GradePrice.objects.create(
        grade_letter='A',
        price_per_unit=Decimal('45.00'),
        effective_from=date.today(),
    )

    yesterday = date.today() - timedelta(days=1)

    client = manager_client

    resp = client.post('/api/deliveries/', {
        'farmer': farmer.id,
        'product_type': 'MILK',
        'volume_litres': '100.00',
        'date_delivered': yesterday.isoformat(),
    }, format='json')
    assert resp.status_code == 201, f'Delivery create failed: {resp.data}'
    delivery_id = resp.data['id']
    delivery_batch = resp.data['batch_id']
    assert Delivery.objects.filter(id=delivery_id).exists()

    resp = grader_client.post('/api/grades/', {
        'delivery': delivery_id,
        'grade_letter': 'A',
        'price_per_unit': '45.00',
    }, format='json')
    assert resp.status_code == 201, f'Grade create failed: {resp.data}'
    grade_id = resp.data['id']
    assert Grade.objects.filter(id=grade_id).exists()
    delivery = Delivery.objects.get(id=delivery_id)
    assert delivery.status == 'GRADED', 'Delivery should be GRADED after grading'

    update_inventory_on_grade(str(grade_id))
    grade = Grade.objects.get(id=grade_id)
    assert grade.is_inventory_updated, 'Inventory should be marked as updated'

    from apps.inventory.models import Inventory
    inventory = Inventory.objects.get(batch_id=delivery_batch)
    assert inventory.quantity_in == Decimal('100.00')

    resp = client.post('/api/sales/', {
        'buyer': buyer.id,
        'line_items': [
            {'inventory': str(inventory.id), 'quantity': '100.00'},
        ],
        'quantity': '100.00',
        'price_per_unit': '45.00',
        'invoice_number': 'SMOKE-INV-001',
    }, format='json')
    assert resp.status_code == 201, f'Sale create failed: {resp.data}'
    sale = Sale.objects.get(invoice_number='SMOKE-INV-001')
    assert sale.total_amount == Decimal('4500.00')

    resp = client.post('/api/payment-engine/', {
        'name': 'Smoke Test Cycle',
        'start_date': (date.today() - timedelta(days=30)).isoformat(),
        'end_date': yesterday.isoformat(),
    }, format='json')
    assert resp.status_code == 201, f'Cycle create failed: {resp.data}'
    cycle_id = resp.data['id']

    with patch('apps.payment_engine.views.run_payment_engine.delay') as mock_delay:
        mock_delay.return_value = MagicMock(id='mock-task-id')
        resp = client.post(f'/api/payment-engine/{cycle_id}/run/')
        assert resp.status_code == 200, f'Run engine failed: {resp.data}'

    cycle = PaymentCycle.objects.get(id=cycle_id)
    farmer_data = compute_fixed_price(cycle)
    assert len(farmer_data) > 0, 'No farmer data computed'
    assert farmer_data[0].total_quantity == 100.0
    assert farmer_data[0].gross_amount == 5000.0  # GradePrice A @ 50.00 * 100 kg

    farmer_payments = []
    for data in farmer_data:
        fp = FarmerPayment(
            cooperative=cycle.cooperative,
            cycle=cycle,
            farmer=data.farmer,
            total_quantity=Decimal(str(data.total_quantity)),
            grade_breakdown=data.grade_breakdown,
            gross_amount=Decimal(str(data.gross_amount)),
            net_amount=Decimal(str(data.gross_amount)),
            deductions={},
            computation_log={
                'method': 'FIXED_PRICE',
                'total_quantity': data.total_quantity,
                'gross_amount': data.gross_amount,
                'deductions_applied': {},
                'net_amount': data.gross_amount,
                'withholding_tax': 0.0,
            },
        )
        farmer_payments.append(fp)
    FarmerPayment.objects.bulk_create(farmer_payments)

    cycle.status = 'COMPUTED'
    cycle.computed_at = timezone.now()
    cycle.save(update_fields=['status', 'computed_at'])

    resp = client.post(f'/api/payment-engine/{cycle_id}/lock/')
    assert resp.status_code == 200, f'Lock cycle failed: {resp.data}'
    cycle.refresh_from_db()
    assert cycle.status == 'LOCKED'

    resp = client.post('/api/disbursements/initiate/', {
        'payment_cycle': str(cycle_id),
    }, format='json')
    assert resp.status_code == 201, f'Initiate disbursement failed: {resp.data}'
    batch_id = resp.data['id']
    assert resp.data['status'] == 'PENDING'
    assert resp.data['total_transactions'] == 1
    assert float(resp.data['total_amount']) == 5000.0

    resp = client.post(f'/api/disbursements/{batch_id}/approve/')
    assert resp.status_code == 200, f'Approve disbursement failed: {resp.data}'
    assert resp.data['approved_by'] is not None
