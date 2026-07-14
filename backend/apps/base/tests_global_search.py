import uuid
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.base.constants import UserRole
from apps.base.views.global_search import GlobalSearchThrottle
from apps.conftest import (
    BuyerFactory,
    CooperativeFactory,
    DeductionFactory,
    DeliveryFactory,
    DisbursementBatchFactory,
    FarmerCooperativeMembershipFactory,
    FarmerFactory,
    FarmerPaymentFactory,
    GradeFactory,
    InventoryFactory,
    LoanFactory,
    PaymentCycleFactory,
    SaleFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db

SEARCH_URL = '/api/search/'


def _auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _make_user(role, cooperative=None, **kwargs):
    return UserFactory(
        role=role,
        cooperative=cooperative,
        is_superuser=(role == UserRole.ADMIN),
        is_staff=(role == UserRole.ADMIN),
        first_name=kwargs.pop('first_name', 'Search'),
        last_name=kwargs.pop('last_name', 'Test'),
        **kwargs,
    )


class TestGlobalSearchValidation:
    def test_empty_query_returns_empty_results(self):
        user = _make_user(UserRole.ADMIN)
        client = _auth_client(user)
        resp = client.get(SEARCH_URL, {'q': ''})
        assert resp.status_code == 200
        assert resp.data['results'] == []

    def test_short_query_returns_empty_results(self):
        user = _make_user(UserRole.ADMIN)
        client = _auth_client(user)
        resp = client.get(SEARCH_URL, {'q': 'a'})
        assert resp.status_code == 200
        assert resp.data['results'] == []

    def test_query_too_long_returns_400(self):
        user = _make_user(UserRole.ADMIN)
        client = _auth_client(user)
        long_q = 'x' * 101
        resp = client.get(SEARCH_URL, {'q': long_q})
        assert resp.status_code == 400
        assert 'error' in resp.data

    def test_unauthenticated_returns_401(self):
        client = APIClient()
        resp = client.get(SEARCH_URL, {'q': 'test'})
        assert resp.status_code == 401


class TestGlobalSearchAdmin:
    def test_admin_searches_all_models(self):
        coop = CooperativeFactory(name='AlphaCoop')
        user = _make_user(UserRole.ADMIN, cooperative=coop)
        client = _auth_client(user)
        farmer = FarmerFactory(first_name='FindMe', cooperative=coop)
        coop2 = CooperativeFactory(name='FindMeCoop')
        resp = client.get(SEARCH_URL, {'q': 'FindMe'})
        assert resp.status_code == 200
        result_keys = {r['key'] for r in resp.data['results']}
        assert 'farmers' in result_keys
        assert 'cooperatives' in result_keys

    def test_admin_results_have_correct_structure(self):
        coop = CooperativeFactory()
        user = _make_user(UserRole.ADMIN, cooperative=coop)
        client = _auth_client(user)
        FarmerFactory(first_name='StructTest', cooperative=coop)
        resp = client.get(SEARCH_URL, {'q': 'StructTest'})
        assert resp.status_code == 200
        for group in resp.data['results']:
            assert 'key' in group
            assert 'label' in group
            assert 'icon' in group
            assert 'total' in group
            assert 'items' in group
            for item in group['items']:
                assert 'id' in item
                assert 'type' in item
                assert 'label' in item
                assert 'subtitle' in item
                assert 'url' in item

    def test_admin_search_no_results(self):
        user = _make_user(UserRole.ADMIN)
        client = _auth_client(user)
        resp = client.get(SEARCH_URL, {'q': 'NoMatchZZZ'})
        assert resp.status_code == 200
        assert resp.data['results'] == []

    def test_admin_urls_correct(self):
        coop = CooperativeFactory()
        user = _make_user(UserRole.ADMIN, cooperative=coop)
        client = _auth_client(user)
        farmer = FarmerFactory(first_name='UrlCheck', cooperative=coop)
        resp = client.get(SEARCH_URL, {'q': 'UrlCheck'})
        assert resp.status_code == 200
        for group in resp.data['results']:
            for item in group['items']:
                assert item['url'].startswith('/admin/')


class TestGlobalSearchManager:
    def test_manager_search_coop_filtered(self):
        coop1 = CooperativeFactory(name='CoopOne')
        coop2 = CooperativeFactory(name='CoopTwo')
        user = _make_user(UserRole.MANAGER, cooperative=coop1, first_name='ManagerX', last_name='UserX')
        client = _auth_client(user)
        f1 = FarmerFactory(first_name='ManagerFind', cooperative=coop1)
        f2 = FarmerFactory(first_name='ManagerFind', cooperative=coop2)
        resp = client.get(SEARCH_URL, {'q': 'ManagerFind'})
        assert resp.status_code == 200
        farmer_group = next((r for r in resp.data['results'] if r['key'] == 'farmers'), None)
        assert farmer_group is not None
        assert farmer_group['total'] == 1

    def test_manager_urls_correct(self):
        coop = CooperativeFactory()
        user = _make_user(UserRole.MANAGER, cooperative=coop)
        client = _auth_client(user)
        FarmerFactory(first_name='MgrUrl', cooperative=coop)
        resp = client.get(SEARCH_URL, {'q': 'MgrUrl'})
        assert resp.status_code == 200
        for group in resp.data['results']:
            for item in group['items']:
                assert item['url'].startswith('/manager/')

    def test_manager_search_returns_relevant_models(self):
        coop = CooperativeFactory()
        user = _make_user(UserRole.MANAGER, cooperative=coop)
        client = _auth_client(user)
        FarmerFactory(first_name='RelMdl', cooperative=coop)
        DeliveryFactory(batch_id='RelMdl-D123', farmer__cooperative=coop)
        resp = client.get(SEARCH_URL, {'q': 'RelMdl'})
        assert resp.status_code == 200
        keys = {r['key'] for r in resp.data['results']}
        assert 'farmers' in keys
        assert 'deliveries' in keys


class TestGlobalSearchAccountant:
    def test_accountant_search_returns_accountant_models(self):
        coop = CooperativeFactory()
        user = _make_user(UserRole.ACCOUNTANT, cooperative=coop)
        client = _auth_client(user)
        farmer = FarmerFactory(first_name='AcctSearch', cooperative=coop)
        loan = LoanFactory(farmer=farmer, cooperative=coop)
        resp = client.get(SEARCH_URL, {'q': 'AcctSearch'})
        assert resp.status_code == 200
        keys = {r['key'] for r in resp.data['results']}
        assert 'farmers' in keys
        assert 'loans' in keys
        assert 'payments' not in keys or any(r['key'] == 'payments' for r in resp.data['results']) is False
        for r in resp.data['results']:
            assert r['key'] in {'farmers', 'loans', 'payment_cycles', 'disbursements', 'deductions', 'payments'}

    def test_accountant_urls_correct(self):
        coop = CooperativeFactory()
        user = _make_user(UserRole.ACCOUNTANT, cooperative=coop)
        client = _auth_client(user)
        FarmerFactory(first_name='AcctUrl', cooperative=coop)
        resp = client.get(SEARCH_URL, {'q': 'AcctUrl'})
        assert resp.status_code == 200
        for group in resp.data['results']:
            for item in group['items']:
                assert item['url'].startswith('/accountant/')


class TestGlobalSearchGrader:
    def test_grader_search_returns_deliveries_and_grades(self):
        coop = CooperativeFactory()
        user = _make_user(UserRole.GRADER, cooperative=coop)
        client = _auth_client(user)
        delivery = DeliveryFactory(batch_id='GraderSearch-BAT', farmer__cooperative=coop)
        GradeFactory(delivery=delivery)
        resp = client.get(SEARCH_URL, {'q': 'GraderSearch'})
        assert resp.status_code == 200
        keys = {r['key'] for r in resp.data['results']}
        assert 'deliveries' in keys
        assert 'grades' in keys
        assert len(resp.data['results']) <= 2

    def test_grader_urls_correct(self):
        coop = CooperativeFactory()
        user = _make_user(UserRole.GRADER, cooperative=coop)
        client = _auth_client(user)
        delivery = DeliveryFactory(batch_id='GraderUrl', farmer__cooperative=coop)
        resp = client.get(SEARCH_URL, {'q': 'GraderUrl'})
        assert resp.status_code == 200
        for group in resp.data['results']:
            for item in group['items']:
                assert item['url'].startswith('/grader/')


class TestGlobalSearchAuditor:
    def test_auditor_search_returns_auditor_models(self):
        coop = CooperativeFactory()
        user = _make_user(UserRole.AUDITOR, cooperative=coop)
        client = _auth_client(user)
        from apps.base.models import AuditLog
        FarmerFactory(first_name='Search', last_name='Match', cooperative=coop)
        AuditLog.objects.create(
            cooperative=coop,
            actor=user,
            resource_type='Farmer',
            resource_id=uuid.uuid4(),
            action='CREATE',
        )
        resp = client.get(SEARCH_URL, {'q': 'Search'})
        assert resp.status_code == 200
        keys = {r['key'] for r in resp.data['results']}
        assert 'farmers' in keys
        assert 'audit_log' in keys

    def test_auditor_urls_correct(self):
        coop = CooperativeFactory()
        user = _make_user(UserRole.AUDITOR, cooperative=coop)
        client = _auth_client(user)
        FarmerFactory(first_name='AudUrl', cooperative=coop)
        resp = client.get(SEARCH_URL, {'q': 'AudUrl'})
        assert resp.status_code == 200
        for group in resp.data['results']:
            for item in group['items']:
                assert item['url'].startswith('/auditor/')


class TestGlobalSearchExternalAuditor:
    def test_external_auditor_search_returns_audit_logs_and_loans(self):
        coop = CooperativeFactory()
        user = _make_user(UserRole.EXTERNAL_AUDITOR, cooperative=coop)
        client = _auth_client(user)
        from apps.base.models import AuditLog
        farmer = FarmerFactory(first_name='ExtAud', cooperative=coop)
        loan = LoanFactory(farmer=farmer, cooperative=coop)
        AuditLog.objects.create(
            cooperative=coop,
            actor=user,
            resource_type='Loan',
            resource_id=loan.id,
            action='VIEW',
        )
        resp = client.get(SEARCH_URL, {'q': 'VIEW'})
        assert resp.status_code == 200
        keys = {r['key'] for r in resp.data['results']}
        assert 'audit_log' in keys
        resp2 = client.get(SEARCH_URL, {'q': 'ExtAud'})
        assert resp2.status_code == 200
        keys2 = {r['key'] for r in resp2.data['results']}
        assert 'loans' in keys2

    def test_external_auditor_urls_correct(self):
        coop = CooperativeFactory()
        user = _make_user(UserRole.EXTERNAL_AUDITOR, cooperative=coop)
        client = _auth_client(user)
        LoanFactory(farmer__cooperative=coop, cooperative=coop)
        resp = client.get(SEARCH_URL, {'q': '10000'})
        assert resp.status_code == 200
        for group in resp.data['results']:
            for item in group['items']:
                assert item['url'].startswith('/external-auditor/')


class TestGlobalSearchFarmer:
    def test_farmer_role_returns_empty_results(self):
        coop = CooperativeFactory()
        user = _make_user(UserRole.FARMER, cooperative=coop)
        client = _auth_client(user)
        FarmerFactory(first_name='FarmerRoleTest', cooperative=coop)
        resp = client.get(SEARCH_URL, {'q': 'FarmerRoleTest'})
        assert resp.status_code == 200
        assert resp.data['results'] == []


class TestGlobalSearchUnknownRole:
    def test_unknown_role_returns_empty_results(self):
        coop = CooperativeFactory()
        user = _make_user('unknown', cooperative=coop)
        client = _auth_client(user)
        FarmerFactory(first_name='UnkRole', cooperative=coop)
        resp = client.get(SEARCH_URL, {'q': 'UnkRole'})
        assert resp.status_code == 200
        assert resp.data['results'] == []
