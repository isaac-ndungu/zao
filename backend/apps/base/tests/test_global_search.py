import pytest
from django.urls import reverse

from apps.base.constants import UserRole
from apps.base.views.global_search import GlobalSearchView
from apps.farmers.models import Farmer

pytestmark = pytest.mark.django_db


class TestGlobalSearchFarmerMemberNumber:
    def test_search_farmer_by_member_number(self, api_client, cooperative):
        user = api_client.user
        user.role = UserRole.ADMIN
        user.save()

        farmer = Farmer.objects.create(
            first_name='June',
            last_name='Kimani',
            phone_number='+254712345678',
            county='Nairobi',
            cooperative=cooperative,
        )
        membership = farmer.memberships.first()
        membership.member_number = 'MEM-JUNE-001'
        membership.save()

        url = reverse('global-search')
        response = api_client.get(url, {'q': 'MEM-JUNE'})
        assert response.status_code == 200

        data = response.json()
        assert data['query'] == 'MEM-JUNE'

        farmer_results = [r for r in data['results'] if r['key'] == 'farmers']
        assert len(farmer_results) == 1
        assert farmer_results[0]['total'] == 1

        item = farmer_results[0]['items'][0]
        assert item['label'] == 'June Kimani'
        assert 'MEM-JUNE-001' in item['subtitle']
        assert item['url'] == f'/admin/farmers/{farmer.id}'

    def test_search_farmer_by_name_still_works(self, api_client, cooperative):
        user = api_client.user
        user.role = UserRole.ADMIN
        user.save()

        Farmer.objects.create(
            first_name='June',
            last_name='Kimani',
            phone_number='+254712345678',
            county='Nairobi',
            cooperative=cooperative,
        )

        url = reverse('global-search')
        response = api_client.get(url, {'q': 'June'})
        assert response.status_code == 200

        data = response.json()
        farmer_results = [r for r in data['results'] if r['key'] == 'farmers']
        assert len(farmer_results) == 1
        assert farmer_results[0]['total'] == 1

    def test_search_farmer_by_phone_still_works(self, api_client, cooperative):
        user = api_client.user
        user.role = UserRole.ADMIN
        user.save()

        Farmer.objects.create(
            first_name='June',
            last_name='Kimani',
            phone_number='+254712345678',
            county='Nairobi',
            cooperative=cooperative,
        )

        url = reverse('global-search')
        response = api_client.get(url, {'q': '254712345678'})
        assert response.status_code == 200

        data = response.json()
        farmer_results = [r for r in data['results'] if r['key'] == 'farmers']
        assert len(farmer_results) == 1
        assert farmer_results[0]['total'] == 1

    def test_id_number_not_searchable(self, api_client, cooperative):
        user = api_client.user
        user.role = UserRole.ADMIN
        user.save()

        Farmer.objects.create(
            first_name='Hidden',
            last_name='Farmer',
            id_number='ID-SECRET-001',
            phone_number='+254799999999',
            county='Nairobi',
            cooperative=cooperative,
        )

        url = reverse('global-search')
        response = api_client.get(url, {'q': 'ID-SECRET'})
        assert response.status_code == 200

        data = response.json()
        farmer_results = [r for r in data['results'] if r['key'] == 'farmers']
        assert len(farmer_results) == 0

    def test_subtitle_shows_n_a_when_no_membership(self, api_client, cooperative):
        user = api_client.user
        user.role = UserRole.ADMIN
        user.save()

        farmer = Farmer.objects.create(
            first_name='Nomatches',
            last_name='Unmatched',
            phone_number='+254788888888',
            county='Nairobi',
            cooperative=cooperative,
        )
        farmer.memberships.first().delete()

        url = reverse('global-search')
        response = api_client.get(url, {'q': 'Nomatches'})
        assert response.status_code == 200

        data = response.json()
        farmer_results = [r for r in data['results'] if r['key'] == 'farmers']
        assert len(farmer_results) == 1
        assert farmer_results[0]['total'] == 1

        item = farmer_results[0]['items'][0]
        assert 'N/A' in item['subtitle']
        assert item['label'] == 'Nomatches Unmatched'
