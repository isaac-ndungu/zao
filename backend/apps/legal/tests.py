from datetime import timedelta

import pytest
from django.utils import timezone

from apps.legal.models import LegalDocument, LegalAcceptance


pytestmark = pytest.mark.django_db


class TestLegalDocumentModel:
    def test_create_document(self):
        doc = LegalDocument.objects.create(
            slug='privacy-policy',
            title='Privacy Policy',
            content='## Test',
            version=1,
            is_active=True,
            published_at=timezone.now(),
        )
        assert doc.slug == 'privacy-policy'
        assert str(doc) == 'privacy-policy v1'

    def test_active_draft_not_returned(self):
        doc = LegalDocument.objects.create(
            slug='privacy-policy',
            title='Privacy Policy',
            content='## Draft',
            version=1,
            is_active=True,
            published_at=None,
        )
        qs = LegalDocument.objects.filter(
            is_active=True,
            published_at__lte=timezone.now(),
        )
        assert not qs.exists()

    def test_future_publish_date_not_returned(self):
        doc = LegalDocument.objects.create(
            slug='privacy-policy',
            title='Privacy Policy',
            content='## Future',
            version=1,
            is_active=True,
            published_at=timezone.now() + timedelta(days=1),
        )
        qs = LegalDocument.objects.filter(
            is_active=True,
            published_at__lte=timezone.now(),
        )
        assert not qs.exists()

    def test_inactive_document_not_returned(self):
        doc = LegalDocument.objects.create(
            slug='privacy-policy',
            title='Privacy Policy',
            content='## Inactive',
            version=1,
            is_active=False,
            published_at=timezone.now(),
        )
        qs = LegalDocument.objects.filter(
            is_active=True,
            published_at__lte=timezone.now(),
        )
        assert not qs.exists()


class TestLegalAcceptanceModel:
    def test_create_acceptance(self, cooperative):
        from apps.conftest import UserFactory
        user = UserFactory(cooperative=cooperative)
        doc = LegalDocument.objects.create(
            slug='privacy-policy',
            title='Privacy Policy',
            content='## Test',
            version=1,
            is_active=True,
            requires_acceptance=True,
            published_at=timezone.now(),
        )
        acceptance = LegalAcceptance.objects.create(
            user=user,
            document=doc,
            version=doc.version,
            ip_address='127.0.0.1',
        )
        assert acceptance.user == user
        assert acceptance.document == doc
        assert acceptance.version == 1
        assert str(acceptance).startswith(f'{user.email} accepted ')

    def test_unique_together_user_document_version(self, cooperative):
        from apps.conftest import UserFactory
        user = UserFactory(cooperative=cooperative)
        doc = LegalDocument.objects.create(
            slug='privacy-policy',
            title='Privacy Policy',
            content='## Test',
            version=1,
            is_active=True,
            requires_acceptance=True,
            published_at=timezone.now(),
        )
        LegalAcceptance.objects.create(
            user=user, document=doc, version=doc.version,
        )
        with pytest.raises(Exception):
            LegalAcceptance.objects.create(
                user=user, document=doc, version=doc.version,
            )


class TestLegalDocumentDetailView:
    def test_get_active_document(self, client):
        doc = LegalDocument.objects.create(
            slug='privacy-policy',
            title='Privacy Policy',
            content='## Test Content',
            version=1,
            is_active=True,
            published_at=timezone.now(),
        )
        resp = client.get('/api/legal/privacy-policy/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['slug'] == 'privacy-policy'
        assert data['title'] == 'Privacy Policy'
        assert data['content'] == '## Test Content'
        assert data['version'] == 1

    def test_unknown_slug_returns_404(self, client):
        resp = client.get('/api/legal/unknown/')
        assert resp.status_code == 404

    def test_draft_document_returns_404(self, client):
        doc = LegalDocument.objects.create(
            slug='privacy-policy',
            title='Privacy Policy',
            content='## Draft',
            version=1,
            is_active=True,
            published_at=None,
        )
        resp = client.get('/api/legal/privacy-policy/')
        assert resp.status_code == 404

    def test_returns_latest_version(self, client):
        doc1 = LegalDocument.objects.create(
            slug='privacy-policy', title='PP v1', content='v1',
            version=1, is_active=True, published_at=timezone.now(),
        )
        doc2 = LegalDocument.objects.create(
            slug='privacy-policy', title='PP v2', content='v2',
            version=2, is_active=True, published_at=timezone.now(),
        )
        resp = client.get('/api/legal/privacy-policy/')
        assert resp.status_code == 200
        assert resp.json()['version'] == 2


class TestLegalDocumentVersionListView:
    def test_lists_versions(self, client):
        doc1 = LegalDocument.objects.create(
            slug='privacy-policy', title='PP v1', content='v1',
            version=1, is_active=True, published_at=timezone.now(),
        )
        doc2 = LegalDocument.objects.create(
            slug='privacy-policy', title='PP v2', content='v2',
            version=2, is_active=True, published_at=timezone.now(),
        )
        resp = client.get('/api/legal/privacy-policy/versions/')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]['version'] == 2
        assert data[1]['version'] == 1
        assert 'content' not in data[0]

    def test_unknown_slug_returns_404(self, client):
        resp = client.get('/api/legal/unknown/versions/')
        assert resp.status_code == 404


class TestLegalDocumentVersionDetailView:
    def test_get_specific_version(self, client):
        doc = LegalDocument.objects.create(
            slug='privacy-policy', title='PP v1', content='v1 content',
            version=1, is_active=True, published_at=timezone.now(),
        )
        resp = client.get('/api/legal/privacy-policy/1/')
        assert resp.status_code == 200
        assert resp.json()['version'] == 1
        assert resp.json()['content'] == 'v1 content'

    def test_unknown_version_returns_404(self, client):
        doc = LegalDocument.objects.create(
            slug='privacy-policy', title='PP v1', content='v1',
            version=1, is_active=True, published_at=timezone.now(),
        )
        resp = client.get('/api/legal/privacy-policy/99/')
        assert resp.status_code == 404


class TestLegalAcceptanceView:
    def test_accept_document(self, api_client):
        doc = LegalDocument.objects.create(
            slug='privacy-policy', title='PP', content='## C',
            version=1, is_active=True, requires_acceptance=True,
            published_at=timezone.now(),
        )
        resp = api_client.post('/api/legal/privacy-policy/accept/')
        assert resp.status_code == 200
        assert LegalAcceptance.objects.filter(
            user=api_client.user, document=doc, version=1
        ).exists()

    def test_accept_non_acceptance_document_returns_400(self, api_client):
        doc = LegalDocument.objects.create(
            slug='privacy-policy', title='PP', content='## C',
            version=1, is_active=True, requires_acceptance=False,
            published_at=timezone.now(),
        )
        resp = api_client.post('/api/legal/privacy-policy/accept/')
        assert resp.status_code == 400

    def test_accept_unknown_slug_returns_404(self, api_client):
        resp = api_client.post('/api/legal/unknown/accept/')
        assert resp.status_code == 404

    def test_accept_requires_auth(self, client):
        resp = client.post('/api/legal/privacy-policy/accept/')
        assert resp.status_code == 401

    def test_accept_is_idempotent(self, api_client):
        doc = LegalDocument.objects.create(
            slug='privacy-policy', title='PP', content='## C',
            version=1, is_active=True, requires_acceptance=True,
            published_at=timezone.now(),
        )
        resp1 = api_client.post('/api/legal/privacy-policy/accept/')
        resp2 = api_client.post('/api/legal/privacy-policy/accept/')
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert LegalAcceptance.objects.count() == 1


class TestPendingAcceptanceView:
    def test_pending_documents_returned(self, api_client):
        doc = LegalDocument.objects.create(
            slug='privacy-policy', title='PP', content='## C',
            version=1, is_active=True, requires_acceptance=True,
            published_at=timezone.now(),
        )
        resp = api_client.get('/api/legal/pending-acceptance/')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data['pending_documents']) == 1
        assert data['pending_documents'][0]['slug'] == 'privacy-policy'

    def test_no_pending_when_accepted(self, api_client):
        doc = LegalDocument.objects.create(
            slug='privacy-policy', title='PP', content='## C',
            version=1, is_active=True, requires_acceptance=True,
            published_at=timezone.now(),
        )
        LegalAcceptance.objects.create(
            user=api_client.user, document=doc, version=doc.version,
        )
        resp = api_client.get('/api/legal/pending-acceptance/')
        assert resp.status_code == 200
        assert len(resp.json()['pending_documents']) == 0

    def test_non_acceptance_document_not_pending(self, api_client):
        doc = LegalDocument.objects.create(
            slug='privacy-policy', title='PP', content='## C',
            version=1, is_active=True, requires_acceptance=False,
            published_at=timezone.now(),
        )
        resp = api_client.get('/api/legal/pending-acceptance/')
        assert resp.status_code == 200
        assert len(resp.json()['pending_documents']) == 0

    def test_requires_auth(self, client):
        resp = client.get('/api/legal/pending-acceptance/')
        assert resp.status_code == 401
