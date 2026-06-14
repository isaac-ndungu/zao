import uuid
import secrets
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.signing import TimestampSigner
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auth_api.models import TwoFactorOTP
from apps.auth_api.serializers import INVITE_TOKEN_SALT
from apps.base.constants import UserRole

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestAdminInvite:
    def test_superuser_creates_invite(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.post('/api/admin/auth/invite/', {
            'email': 'invited@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data['detail'] == 'Invite sent.'
        assert data['email'] == 'invited@example.com'
        assert data['role'] == 'manager'
        assert 'invite_token' in data

        user = User.objects.get(email='invited@example.com')
        assert user.is_active is False
        assert user.must_change_password is True
        assert user.role == UserRole.MANAGER

    def test_creates_otp(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        client.post('/api/admin/auth/invite/', {
            'email': 'invited@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
        })
        user = User.objects.get(email='invited@example.com')
        otp = TwoFactorOTP.objects.filter(user=user, purpose='ACTION_CONFIRM').first()
        assert otp is not None
        assert otp.expires_at > timezone.now()
        assert not otp.is_used

    def test_non_superuser_cannot_create(self, api_client):
        api_client.user.is_superuser = False
        api_client.user.save(update_fields=['is_superuser'])
        resp = api_client.post('/api/admin/auth/invite/', {
            'email': 'invited@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
        })
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create(self, client):
        resp = client.post('/api/admin/auth/invite/', {
            'email': 'invited@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
        })
        assert resp.status_code == 401

    def test_superuser_revokes_invite(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)

        resp = client.post('/api/admin/auth/invite/', {
            'email': 'invited@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
        })
        user_id = User.objects.get(email='invited@example.com').id

        resp = client.post(f'/api/admin/auth/invite/{user_id}/revoke/', {
            'confirm': True,
        })
        assert resp.status_code == 200
        assert resp.json()['detail'] == 'Invite revoked.'

        user = User.objects.get(id=user_id)
        assert user.invite_revoked is True

        otps = TwoFactorOTP.objects.filter(user=user, purpose='ACTION_CONFIRM', is_used=False)
        assert otps.count() == 0

    def test_revoke_non_existent_user(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        fake_id = uuid.uuid4()
        resp = client.post(f'/api/admin/auth/invite/{fake_id}/revoke/', {
            'confirm': True,
        })
        assert resp.status_code == 404

    def test_revoke_requires_confirm(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)

        client.post('/api/admin/auth/invite/', {
            'email': 'invited@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
        })
        user_id = User.objects.get(email='invited@example.com').id

        resp = client.post(f'/api/admin/auth/invite/{user_id}/revoke/', {
            'confirm': False,
        })
        assert resp.status_code == 400

    def test_revoked_invite_cannot_verify(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)

        client.post('/api/admin/auth/invite/', {
            'email': 'invited@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
        })
        user = User.objects.get(email='invited@example.com')
        otp = TwoFactorOTP.objects.filter(user=user, purpose='ACTION_CONFIRM').first()

        client.post(f'/api/admin/auth/invite/{user.id}/revoke/', {
            'confirm': True,
        })

        signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
        invite_token = signer.sign(user.email)

        unauth_client = APIClient()
        resp = unauth_client.post('/api/auth/invite/verify/', {
            'invite_token': invite_token,
            'otp_code': otp.otp_code,
            'password': 'newpass123',
            'phone_number': '+254700000099',
        })
        assert resp.status_code == 400


class TestAdminInviteDuplicateEmail:
    def test_duplicate_email_validation(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        client.post('/api/admin/auth/invite/', {
            'email': 'invited@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
        })
        resp = client.post('/api/admin/auth/invite/', {
            'email': 'invited@example.com',
            'first_name': 'Another',
            'last_name': 'User',
        })
        assert resp.status_code == 400
