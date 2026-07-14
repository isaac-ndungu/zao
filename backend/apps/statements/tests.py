import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status

from apps.base.constants import UserRole
from apps.base.models import AuditLog


# Helper: generate unique 13-digit phone numbers to avoid DB constraint clashes
_phone_counter = 0


def _phone():
    global _phone_counter
    _phone_counter += 1
    return f'+2547{_phone_counter:09d}'

pytestmark = pytest.mark.django_db


# =============================================================================
# Authentication tests — all endpoints return 401 when unauthenticated
# =============================================================================


class TestAuthentication:
    def test_statement_pdf_unauthenticated(self, client):
        resp = client.get('/api/statements/statement/', {'farmer_payment_id': uuid.uuid4()})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_latest_statement_unauthenticated(self, client):
        resp = client.get('/api/statements/statement/latest/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_payment_history_unauthenticated(self, client):
        resp = client.get('/api/statements/statement/history/', {'farmer_id': uuid.uuid4()})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_season_report_unauthenticated(self, client):
        resp = client.get('/api/statements/report/', {'cycle_id': uuid.uuid4()})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_kra_report_unauthenticated(self, client):
        resp = client.get('/api/statements/kra-report/', {'year': 2026})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_annual_report_unauthenticated(self, client):
        resp = client.get('/api/statements/annual-report/', {'year': 2026})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_audit_log_unauthenticated(self, client):
        resp = client.get('/api/statements/audit/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_external_audit_unauthenticated(self, client):
        resp = client.get('/api/statements/external-audit/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Permission-role tests — wrong roles get 403
# =============================================================================


class TestPermissionRoles:
    """Verify that views with extra role requirements reject wrong roles."""

    def _make_user(self, role, cooperative):
        from apps.auth_api.models import User
        return User.objects.create(
            email=f'{role}@test.com', phone_number=_phone(),
            role=role, cooperative=cooperative,
        )

    # -- LatestStatementPDFView: IsAuthenticated + IsFarmer --

    def test_latest_statement_non_farmer_403(self, api_client, cooperative):
        """Manager (non-Farmer) gets 403."""
        user = self._make_user(UserRole.MANAGER, cooperative)
        api_client.force_authenticate(user=user)
        resp = api_client.get('/api/statements/statement/latest/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    # -- SeasonReportPDFView: IsAuthenticated + (IsAccountantOrManager | IsAnyAuditor) --

    def test_season_report_farmer_403(self, api_client, cooperative):
        user = self._make_user(UserRole.FARMER, cooperative)
        api_client.force_authenticate(user=user)
        resp = api_client.get('/api/statements/report/', {'cycle_id': uuid.uuid4()})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_season_report_grader_403(self, api_client, cooperative):
        user = self._make_user(UserRole.GRADER, cooperative)
        api_client.force_authenticate(user=user)
        resp = api_client.get('/api/statements/report/', {'cycle_id': uuid.uuid4()})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    # -- KRAReportPDFView: same permission as SeasonReport --

    def test_kra_report_farmer_403(self, api_client, cooperative):
        user = self._make_user(UserRole.FARMER, cooperative)
        api_client.force_authenticate(user=user)
        resp = api_client.get('/api/statements/kra-report/', {'year': 2026})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    # -- AnnualReportView: same permission --

    def test_annual_report_farmer_403(self, api_client, cooperative):
        user = self._make_user(UserRole.FARMER, cooperative)
        api_client.force_authenticate(user=user)
        resp = api_client.get('/api/statements/annual-report/', {'year': 2026})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    # -- AuditLogViewSet: IsAuthenticated + IsManagerOrAuditor --

    @pytest.mark.parametrize('role', [UserRole.FARMER, UserRole.GRADER, UserRole.ACCOUNTANT])
    def test_audit_log_non_manager_403(self, api_client, cooperative, role):
        user = self._make_user(role, cooperative)
        api_client.force_authenticate(user=user)
        resp = api_client.get('/api/statements/audit/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    # -- ExternalAuditLogViewSet: IsAuthenticated + IsExternalAuditor --

    @pytest.mark.parametrize('role', [
        UserRole.FARMER, UserRole.MANAGER, UserRole.ACCOUNTANT,
        UserRole.GRADER, UserRole.AUDITOR, UserRole.ADMIN,
    ])
    def test_external_audit_non_external_auditor_403(self, api_client, cooperative, role):
        user = self._make_user(role, cooperative)
        api_client.force_authenticate(user=user)
        resp = api_client.get('/api/statements/external-audit/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# StatementPDFView
# =============================================================================


class TestStatementPDFView:
    URL = '/api/statements/statement/'

    def test_missing_farmer_payment_id_400(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'farmer_payment_id' in resp.json()['error']

    def test_non_existent_payment_admin_404(self, api_client):
        """Admin role (default api_client) looks up FarmerPayment directly."""
        resp = api_client.get(self.URL, {'farmer_payment_id': uuid.uuid4()})
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert 'FarmerPayment not found' in resp.json()['error']

    @patch('apps.statements.views.generate_farmer_statement')
    def test_non_admin_non_existent_payment_404(self, mock_generate, api_client, cooperative):
        """Non-admin passes cooperative_id to generate; mock returns error."""
        from apps.auth_api.models import User
        user = User.objects.create(
            email='mgr@test.com', phone_number=_phone(),
            role=UserRole.MANAGER, cooperative=cooperative,
        )
        api_client.force_authenticate(user=user)
        mock_generate.return_value = (None, None, 'FarmerPayment not found')

        resp = api_client.get(self.URL, {'farmer_payment_id': uuid.uuid4()})
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        mock_generate.assert_called_once()

    @patch('apps.statements.views.generate_farmer_statement')
    def test_valid_payment_returns_pdf(self, mock_generate, api_client, cooperative):
        from apps.farmers.models import Farmer
        from apps.payment_engine.models import FarmerPayment, PaymentCycle
        farmer = Farmer.objects.create(
            first_name='A', last_name='B', email='a@b.com',
            id_number='ID999', phone_number=_phone(),
            county='Nairobi', cooperative=cooperative,
        )
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative, name='Cycle 1',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() - timedelta(days=1),
            status='COMPUTED',
        )
        fp = FarmerPayment.objects.create(
            cycle=cycle, cooperative=cooperative, farmer=farmer,
            total_quantity=Decimal('100'), gross_amount=Decimal('4500'),
            net_amount=Decimal('4300'),
        )
        mock_generate.return_value = (b'%PDF-1.4 mock', 'statement.pdf', None)

        resp = api_client.get(self.URL, {'farmer_payment_id': fp.id})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.get('Content-Type') == 'application/pdf'
        assert resp.get('Content-Disposition') is not None

    @patch('apps.statements.views.generate_farmer_statement')
    def test_farmer_can_view_own_statement(self, mock_generate, api_client, cooperative):
        from apps.auth_api.models import User
        from apps.farmers.models import Farmer
        from apps.payment_engine.models import FarmerPayment, PaymentCycle

        farmer_user = User.objects.create(
            email='fowner@test.com', phone_number=_phone(),
            role=UserRole.FARMER, cooperative=cooperative,
        )
        farmer = Farmer.objects.create(
            first_name='Owner', last_name='Farmer', email='fo@t.com',
            id_number='ID666', phone_number=_phone(),
            county='Nairobi', cooperative=cooperative,
            user=farmer_user,
        )
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative, name='C1',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() - timedelta(days=1),
            status='COMPUTED',
        )
        fp = FarmerPayment.objects.create(
            cycle=cycle, cooperative=cooperative, farmer=farmer,
            total_quantity=Decimal('50'), gross_amount=Decimal('2000'),
            net_amount=Decimal('1900'),
        )
        mock_generate.return_value = (b'%PDF-1.4 mock', 'stmt.pdf', None)
        api_client.force_authenticate(user=farmer_user)

        resp = api_client.get(self.URL, {'farmer_payment_id': fp.id})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.get('Content-Type') == 'application/pdf'


# =============================================================================
# LatestStatementPDFView
# =============================================================================


class TestLatestStatementPDFView:
    URL = '/api/statements/statement/latest/'

    @patch('apps.statements.views.generate_farmer_statement')
    def test_returns_latest_paid_payment_pdf(self, mock_generate, api_client, cooperative):
        from apps.auth_api.models import User
        from apps.farmers.models import Farmer
        from apps.payment_engine.models import FarmerPayment, PaymentCycle

        farmer_user = User.objects.create(
            email='flatest@test.com', phone_number=_phone(),
            role=UserRole.FARMER, cooperative=cooperative,
        )
        farmer = Farmer.objects.create(
            first_name='Latest', last_name='Farmer', email='la@t.com',
            id_number='ID555', phone_number=_phone(),
            county='Nairobi', cooperative=cooperative,
            user=farmer_user,
        )
        cycle_later = PaymentCycle.objects.create(
            cooperative=cooperative, name='Cycle B',
            start_date=date(2025, 3, 1), end_date=date(2025, 3, 31),
            status='LOCKED',
        )
        cycle_earlier = PaymentCycle.objects.create(
            cooperative=cooperative, name='Cycle A',
            start_date=date(2025, 2, 1), end_date=date(2025, 2, 28),
            status='LOCKED',
        )
        # Create later payment first (should be returned by .order_by('-cycle__end_date'))
        FarmerPayment.objects.create(
            cycle=cycle_later, cooperative=cooperative, farmer=farmer,
            total_quantity=Decimal('100'), gross_amount=Decimal('4500'),
            net_amount=Decimal('4300'), payment_status='PAID',
        )
        FarmerPayment.objects.create(
            cycle=cycle_earlier, cooperative=cooperative, farmer=farmer,
            total_quantity=Decimal('50'), gross_amount=Decimal('2000'),
            net_amount=Decimal('1900'), payment_status='PAID',
        )
        mock_generate.return_value = (b'%PDF-1.4 mock', 'latest.pdf', None)
        api_client.force_authenticate(user=farmer_user)

        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.get('Content-Type') == 'application/pdf'

    def test_no_farmer_profile_404(self, api_client, cooperative):
        from apps.auth_api.models import User
        user = User.objects.create(
            email='nofarmer@test.com', phone_number=_phone(),
            role=UserRole.FARMER, cooperative=cooperative,
        )
        api_client.force_authenticate(user=user)

        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert 'No farmer profile' in resp.json()['error']

    def test_no_paid_payments_404(self, api_client, cooperative, farmer):
        from apps.auth_api.models import User
        farmer_user = User.objects.create(
            email='nopay@test.com', phone_number=_phone(),
            role=UserRole.FARMER, cooperative=cooperative,
        )
        farmer.user = farmer_user
        farmer.save()

        api_client.force_authenticate(user=farmer_user)
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert 'No completed payment' in resp.json()['error']


# =============================================================================
# FarmerPaymentHistoryView
# =============================================================================


class TestFarmerPaymentHistoryView:
    URL = '/api/statements/statement/history/'

    def test_missing_farmer_id_400(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'farmer_id' in resp.json()['error']

    def test_non_existent_farmer_404(self, api_client):
        resp = api_client.get(self.URL, {'farmer_id': uuid.uuid4()})
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert 'Farmer not found' in resp.json()['error']

    def test_farmer_can_only_see_own_history_403(self, api_client, cooperative):
        from apps.auth_api.models import User
        from apps.farmers.models import Farmer

        farmer_user = User.objects.create(
            email='ownhist@test.com', phone_number=_phone(),
            role=UserRole.FARMER, cooperative=cooperative,
        )
        other_farmer = Farmer.objects.create(
            first_name='Other', last_name='F', email='o@t.com',
            id_number='ID777', phone_number=_phone(),
            county='Nairobi', cooperative=cooperative,
        )
        api_client.force_authenticate(user=farmer_user)

        resp = api_client.get(self.URL, {'farmer_id': other_farmer.id})
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert 'own payment history' in resp.json()['error']

    def test_farmer_cooperative_mismatch_404(self, api_client):
        """Non-admin user from coop A cannot see farmer from coop B."""
        from apps.auth_api.models import User
        from apps.farmers.models import Farmer
        from apps.cooperatives.models import Cooperative

        coop_a = Cooperative.objects.create(
            name='Coop A', registration_number='REG001',
            county='Nairobi', sub_county='Westlands',
            produce_type='DAIRY', payment_model='FIXED_PRICE',
            levy_percentage=Decimal('2.00'), monthly_fee=Decimal('100'),
            is_active=True, prefix='CA', mpesa_shortcode='111111',
        )
        coop_b = Cooperative.objects.create(
            name='Coop B', registration_number='REG002',
            county='Nairobi', sub_county='Westlands',
            produce_type='DAIRY', payment_model='FIXED_PRICE',
            levy_percentage=Decimal('2.00'), monthly_fee=Decimal('100'),
            is_active=True, prefix='CB', mpesa_shortcode='222222',
        )
        user = User.objects.create(
            email='mgrcoop@test.com', phone_number=_phone(),
            role=UserRole.MANAGER, cooperative=coop_a,
        )
        farmer_b = Farmer.objects.create(
            first_name='CoopB', last_name='Farmer', email='cb@t.com',
            id_number='ID888', phone_number=_phone(),
            county='Nairobi', cooperative=coop_b,
        )
        api_client.force_authenticate(user=user)

        resp = api_client.get(self.URL, {'farmer_id': farmer_b.id})
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert 'Farmer not found in your cooperative' in resp.json()['error']

    def test_returns_payment_history(self, api_client, cooperative):
        from apps.auth_api.models import User
        from apps.farmers.models import Farmer
        from apps.payment_engine.models import FarmerPayment, PaymentCycle

        farmer = Farmer.objects.create(
            first_name='History', last_name='Test', email='ht@t.com',
            id_number='ID999', phone_number=_phone(),
            county='Nairobi', cooperative=cooperative,
        )
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative, name='Cycle H',
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() - timedelta(days=1),
            status='LOCKED',
        )
        FarmerPayment.objects.create(
            cycle=cycle, cooperative=cooperative, farmer=farmer,
            total_quantity=Decimal('100'), gross_amount=Decimal('4500'),
            net_amount=Decimal('4300'), payment_status='PAID',
        )

        resp = api_client.get(self.URL, {'farmer_id': farmer.id})
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data['farmer_id'] == str(farmer.id)
        assert 'farmer_name' in data
        assert 'payments' in data
        assert len(data['payments']) == 1
        p = data['payments'][0]
        assert 'farmer_payment_id' in p
        assert 'cycle_name' in p
        assert 'period_start' in p
        assert 'period_end' in p
        assert 'gross_amount' in p
        assert 'net_amount' in p
        assert 'status' in p


# =============================================================================
# SeasonReportPDFView
# =============================================================================


class TestSeasonReportPDFView:
    URL = '/api/statements/report/'

    def test_missing_cycle_id_400(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'cycle_id' in resp.json()['error']

    @patch('apps.statements.views.generate_season_report')
    def test_valid_cycle_returns_pdf(self, mock_generate, api_client, cooperative):
        from apps.payment_engine.models import PaymentCycle
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative, name='Season C',
            start_date=date(2025, 1, 1), end_date=date(2025, 3, 31),
            status='COMPUTED',
        )
        mock_generate.return_value = (b'%PDF-1.4 mock', 'season.pdf', None)

        resp = api_client.get(self.URL, {'cycle_id': cycle.id})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.get('Content-Type') == 'application/pdf'

    @patch('apps.statements.views.generate_season_report')
    def test_farmer_count_over_200_400(self, mock_generate, api_client, cooperative):
        from apps.payment_engine.models import PaymentCycle
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative, name='Big C',
            start_date=date(2025, 1, 1), end_date=date(2025, 3, 31),
            status='COMPUTED',
        )
        mock_generate.return_value = (
            None, None,
            'Season report generation is not supported for cooperatives '
            'with over 200 farmers in this version. Please contact support.',
        )

        resp = api_client.get(self.URL, {'cycle_id': cycle.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'over 200' in resp.json()['error']


# =============================================================================
# KRAReportPDFView
# =============================================================================


class TestKRAReportPDFView:
    URL = '/api/statements/kra-report/'

    def test_missing_year_400(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'year' in resp.json()['error']

    @pytest.mark.parametrize('bad_year', ['abcd', 1800, 2100, -1, 0])
    def test_invalid_year_400(self, api_client, bad_year):
        resp = api_client.get(self.URL, {'year': bad_year})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'year must be a valid' in resp.json()['error']

    @patch('apps.statements.views.generate_kra_report')
    def test_valid_year_returns_pdf(self, mock_generate, api_client, cooperative):
        mock_generate.return_value = (b'%PDF-1.4 mock', 'kra.pdf', None)

        resp = api_client.get(self.URL, {'year': 2026})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.get('Content-Type') == 'application/pdf'

    @patch('apps.statements.views.generate_kra_report')
    def test_accountant_can_access(self, mock_generate, api_client, cooperative):
        from apps.auth_api.models import User
        user = User.objects.create(
            email='acc@test.com', phone_number=_phone(),
            role=UserRole.ACCOUNTANT, cooperative=cooperative,
        )
        api_client.force_authenticate(user=user)
        mock_generate.return_value = (b'%PDF-1.4 mock', 'kra.pdf', None)

        resp = api_client.get(self.URL, {'year': 2026})
        assert resp.status_code == status.HTTP_200_OK

    @patch('apps.statements.views.generate_kra_report')
    def test_auditor_can_access(self, mock_generate, api_client, cooperative):
        from apps.auth_api.models import User
        user = User.objects.create(
            email='aud@test.com', phone_number=_phone(),
            role=UserRole.AUDITOR, cooperative=cooperative,
        )
        api_client.force_authenticate(user=user)
        mock_generate.return_value = (b'%PDF-1.4 mock', 'kra.pdf', None)

        resp = api_client.get(self.URL, {'year': 2026})
        assert resp.status_code == status.HTTP_200_OK


# =============================================================================
# AnnualReportView
# =============================================================================


class TestAnnualReportView:
    URL = '/api/statements/annual-report/'

    def test_missing_year_400(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'year' in resp.json()['error']

    @pytest.mark.parametrize('bad_year', ['xyz', 1899, 2100])
    def test_invalid_year_400(self, api_client, bad_year):
        resp = api_client.get(self.URL, {'year': bad_year})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'year must be a valid' in resp.json()['error']

    def test_returns_json_structure(self, api_client, cooperative):
        """Full integration test — creates real data and validates response shape."""
        from apps.auth_api.models import User
        from apps.deliveries.models import Delivery
        from apps.farmers.models import Farmer
        from apps.payment_engine.models import FarmerPayment, PaymentCycle
        from apps.sales.models import Buyer, Sale

        # Build data for FY 2025 (Jul 2025 – Jun 2026)
        fy_start = date(2025, 7, 1)
        fy_end = date(2026, 6, 30)
        cycle = PaymentCycle.objects.create(
            cooperative=cooperative, name='FY Cycle',
            start_date=date(2025, 8, 1),
            end_date=date(2025, 8, 31),
            status='LOCKED',
        )
        farmer = Farmer.objects.create(
            first_name='Ann', last_name='Report', email='ar@t.com',
            id_number='ID1001', phone_number=_phone(),
            county='Nairobi', cooperative=cooperative,
        )
        FarmerPayment.objects.create(
            cycle=cycle, cooperative=cooperative, farmer=farmer,
            total_quantity=Decimal('200'), gross_amount=Decimal('9000'),
            net_amount=Decimal('8600'), payment_status='PAID',
            withholding_tax_amount=Decimal('100'),
        )
        Delivery.objects.create(
            farmer=farmer, cooperative=cooperative,
            product_type='MILK', quantity_kg=Decimal('200'),
            status='APPROVED',
            date_delivered=timezone.make_aware(datetime(2025, 8, 15)),
            batch_id='BAT-ANNUAL',
        )
        buyer = Buyer.objects.create(
            cooperative=cooperative, name='Test Buyer',
            phone_number=_phone(), is_active=True,
        )
        Sale.objects.create(
            buyer=buyer, cooperative=cooperative,
            product_type='MILK', grade_letter='A', unit='kg',
            quantity=Decimal('200'), price_per_unit=Decimal('45'),
            total_amount=Decimal('9000'), status='COMPLETED',
            sale_date=date(2025, 8, 15),
        )

        resp = api_client.get(self.URL, {'year': 2025})
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()

        assert data['financial_year'] == '2025/2026'
        assert 'period' in data
        assert data['period']['start'] == '2025-07-01'
        assert data['period']['end'] == '2026-06-30'

        summary = data['summary']
        assert 'total_produce_received' in summary
        assert 'MILK' in summary['total_produce_received']
        assert summary['total_revenue'] == 9000.0
        assert summary['total_farmer_payments'] == 8600.0
        assert 'total_deductions_collected' in summary
        assert summary['total_withholding_tax_held'] == 100.0
        assert summary['cycle_count'] >= 1

        assert 'farmer_summaries' in data
        assert len(data['farmer_summaries']) == 1
        fs = data['farmer_summaries'][0]
        assert fs['farmer_id'] == str(farmer.id)
        assert 'farmer_name' in fs
        assert fs['total_quantity'] == 200.0
        assert fs['total_gross'] == 9000.0
        assert fs['total_net'] == 8600.0
        assert fs['payment_count'] == 1

    def test_admin_can_access_any_cooperative(self, api_client):
        """Admin user can see reports without cooperative scope."""
        resp = api_client.get(self.URL, {'year': 2025})
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert 'summary' in data
        assert 'farmer_summaries' in data


# =============================================================================
# AuditLogViewSet
# =============================================================================


class TestAuditLogViewSet:
    URL = '/api/statements/audit/'

    def _create_logs(self, cooperative, actor, count=3):
        logs = []
        for i in range(count):
            logs.append(AuditLog(
                cooperative=cooperative,
                actor=actor,
                resource_type='FarmerPayment',
                resource_id=uuid.uuid4(),
                action='CREATE',
                ip_address='127.0.0.1',
            ))
        return AuditLog.objects.bulk_create(logs)

    def test_list_returns_paginated_results(self, api_client, cooperative):
        from apps.auth_api.models import User
        user = User.objects.create(
            email='mgr_aud@test.com', phone_number=_phone(),
            role=UserRole.MANAGER, cooperative=cooperative,
        )
        self._create_logs(cooperative, user, count=3)
        api_client.force_authenticate(user=user)

        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert 'count' in data
        assert data['count'] == 3
        assert 'results' in data
        assert len(data['results']) == 3

    def test_filter_by_resource_type(self, api_client, cooperative):
        from apps.auth_api.models import User
        user = User.objects.create(
            email='mgr_filt@test.com', phone_number=_phone(),
            role=UserRole.MANAGER, cooperative=cooperative,
        )
        self._create_logs(cooperative, user, count=2)
        AuditLog.objects.create(
            cooperative=cooperative, actor=user,
            resource_type='PaymentCycle', resource_id=uuid.uuid4(),
            action='LOCK', ip_address='127.0.0.1',
        )
        api_client.force_authenticate(user=user)

        resp = api_client.get(self.URL, {'resource_type': 'PaymentCycle'})
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data['count'] == 1
        assert data['results'][0]['resource_type'] == 'PaymentCycle'

    def test_filter_by_action(self, api_client, cooperative):
        from apps.auth_api.models import User
        user = User.objects.create(
            email='mgr_act@test.com', phone_number=_phone(),
            role=UserRole.MANAGER, cooperative=cooperative,
        )
        self._create_logs(cooperative, user, count=2)
        AuditLog.objects.create(
            cooperative=cooperative, actor=user,
            resource_type='FarmerPayment', resource_id=uuid.uuid4(),
            action='LOCK', ip_address='127.0.0.1',
        )
        api_client.force_authenticate(user=user)

        resp = api_client.get(self.URL, {'action': 'LOCK'})
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data['count'] == 1
        assert data['results'][0]['action'] == 'LOCK'

    def test_filter_by_action_category_financial(self, api_client, cooperative):
        from apps.auth_api.models import User
        user = User.objects.create(
            email='mgr_cat@test.com', phone_number=_phone(),
            role=UserRole.MANAGER, cooperative=cooperative,
        )
        AuditLog.objects.create(
            cooperative=cooperative, actor=user,
            resource_type='FarmerPayment', resource_id=uuid.uuid4(),
            action='LOCK', ip_address='127.0.0.1',
        )
        AuditLog.objects.create(
            cooperative=cooperative, actor=user,
            resource_type='Delivery', resource_id=uuid.uuid4(),
            action='CREATE', ip_address='127.0.0.1',
        )
        api_client.force_authenticate(user=user)

        resp = api_client.get(self.URL, {'action_category': 'financial'})
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        # Delivery is not in _FINANCIAL_RESOURCE_TYPES, so only 1 matches
        assert data['count'] == 1

    def test_filter_by_date_range(self, api_client, cooperative):
        from apps.auth_api.models import User
        from django.db.models.functions import Now
        from django.db.models import DateTimeField

        user = User.objects.create(
            email='mgr_date@test.com', phone_number=_phone(),
            role=UserRole.MANAGER, cooperative=cooperative,
        )
        AuditLog.objects.create(
            cooperative=cooperative, actor=user,
            resource_type='FarmerPayment', resource_id=uuid.uuid4(),
            action='CREATE', ip_address='127.0.0.1',
        )
        api_client.force_authenticate(user=user)

        resp = api_client.get(self.URL, {
            'date_from': (timezone.now() - timedelta(days=1)).isoformat(),
            'date_to': (timezone.now() + timedelta(days=1)).isoformat(),
        })
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data['count'] >= 1

    def test_cooperative_scoped_non_admin(self, api_client):
        """Non-admin users only see logs from their own cooperative."""
        from apps.auth_api.models import User
        from apps.cooperatives.models import Cooperative

        coop_a = Cooperative.objects.create(
            name='Audit A', registration_number='REG-AUD-A',
            county='Nairobi', sub_county='Westlands',
            produce_type='DAIRY', payment_model='FIXED_PRICE',
            levy_percentage=Decimal('2.00'), monthly_fee=Decimal('100'),
            is_active=True, prefix='AA', mpesa_shortcode='333333',
        )
        coop_b = Cooperative.objects.create(
            name='Audit B', registration_number='REG-AUD-B',
            county='Nairobi', sub_county='Westlands',
            produce_type='DAIRY', payment_model='FIXED_PRICE',
            levy_percentage=Decimal('2.00'), monthly_fee=Decimal('100'),
            is_active=True, prefix='BB', mpesa_shortcode='444444',
        )
        user_a = User.objects.create(
            email='audit_a@test.com', phone_number=_phone(),
            role=UserRole.MANAGER, cooperative=coop_a,
        )
        user_b = User.objects.create(
            email='audit_b@test.com', phone_number=_phone(),
            role=UserRole.MANAGER, cooperative=coop_b,
        )
        AuditLog.objects.create(
            cooperative=coop_a, actor=user_a,
            resource_type='FarmerPayment', resource_id=uuid.uuid4(),
            action='CREATE', ip_address='127.0.0.1',
        )
        AuditLog.objects.create(
            cooperative=coop_b, actor=user_b,
            resource_type='FarmerPayment', resource_id=uuid.uuid4(),
            action='UPDATE', ip_address='127.0.0.1',
        )
        api_client.force_authenticate(user=user_a)

        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data['count'] == 1
        assert data['results'][0]['action'] == 'CREATE'

    def test_admin_sees_all_cooperatives(self, api_client):
        """Admin (default api_client user) sees logs across all cooperatives."""
        from apps.cooperatives.models import Cooperative

        coop = Cooperative.objects.create(
            name='AdminAudit', registration_number='REG-ADM-AUD',
            county='Nairobi', sub_county='Westlands',
            produce_type='DAIRY', payment_model='FIXED_PRICE',
            levy_percentage=Decimal('2.00'), monthly_fee=Decimal('100'),
            is_active=True, prefix='AD', mpesa_shortcode='555555',
        )
        AuditLog.objects.create(
            cooperative=coop, actor=api_client.user,
            resource_type='FarmerPayment', resource_id=uuid.uuid4(),
            action='DELETE', ip_address='127.0.0.1',
        )

        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        # admin user is from a different cooperative, but should still see all
        assert data['count'] >= 1


# =============================================================================
# ExternalAuditLogViewSet
# =============================================================================


class TestExternalAuditLogViewSet:
    URL = '/api/statements/external-audit/'

    def test_external_auditor_list_returns_financial_only(self, api_client, cooperative):
        from apps.auth_api.models import User

        ext_auditor = User.objects.create(
            email='ext@test.com', phone_number=_phone(),
            role=UserRole.EXTERNAL_AUDITOR, cooperative=cooperative,
        )
        api_client.force_authenticate(user=ext_auditor)

        # Financial entry — should appear
        AuditLog.objects.create(
            cooperative=cooperative, actor=ext_auditor,
            resource_type='FarmerPayment', resource_id=uuid.uuid4(),
            action='LOCK', ip_address='127.0.0.1',
        )
        # Non-financial entry — should NOT appear
        AuditLog.objects.create(
            cooperative=cooperative, actor=ext_auditor,
            resource_type='Delivery', resource_id=uuid.uuid4(),
            action='CREATE', ip_address='127.0.0.1',
        )

        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data['count'] == 1
        assert data['results'][0]['resource_type'] == 'FarmerPayment'
        assert data['results'][0]['action'] == 'LOCK'

    def test_paginated_response(self, api_client, cooperative):
        from apps.auth_api.models import User

        ext_auditor = User.objects.create(
            email='ext2@test.com', phone_number=_phone(),
            role=UserRole.EXTERNAL_AUDITOR, cooperative=cooperative,
        )
        api_client.force_authenticate(user=ext_auditor)

        for _ in range(3):
            AuditLog.objects.create(
                cooperative=cooperative, actor=ext_auditor,
                resource_type='PaymentCycle', resource_id=uuid.uuid4(),
                action='RUN', ip_address='127.0.0.1',
            )

        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data['count'] == 3
        assert len(data['results']) == 3
