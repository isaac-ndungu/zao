import uuid
import secrets
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.mail import send_mail
from django.core.signing import TimestampSigner
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auth_api.models import TwoFactorOTP
from apps.auth_api.serializers import INVITE_TOKEN_SALT
from apps.base.constants import UserRole
from apps.cooperatives.models import Cooperative

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


class TestAdminInviteList:
    def test_list_invites(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        client.post('/api/admin/auth/invite/', {
            'email': 'invited@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
        })
        resp = client.get('/api/admin/auth/invites/')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data['results']) == 1
        assert data['results'][0]['email'] == 'invited@example.com'
        assert data['results'][0]['status'] == 'PENDING'

    def test_list_invites_empty(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get('/api/admin/auth/invites/')
        assert resp.status_code == 200
        assert resp.json()['count'] == 0

    def test_list_invites_filter_by_status(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        client.post('/api/admin/auth/invite/', {
            'email': 'invited@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
        })
        resp = client.get('/api/admin/auth/invites/?status=PENDING')
        assert resp.status_code == 200
        assert resp.json()['count'] == 1

        resp = client.get('/api/admin/auth/invites/?status=ACCEPTED')
        assert resp.status_code == 200
        assert resp.json()['count'] == 0


class TestAdminInviteDetail:
    def test_invite_detail(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        client.post('/api/admin/auth/invite/', {
            'email': 'invited@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
        })
        user = User.objects.get(email='invited@example.com')
        resp = client.get(f'/api/admin/auth/invites/{user.id}/')
        assert resp.status_code == 200
        assert resp.json()['email'] == 'invited@example.com'
        assert resp.json()['status'] == 'PENDING'

    def test_invite_detail_not_found(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.get(f'/api/admin/auth/invites/{uuid.uuid4()}/')
        assert resp.status_code == 404


class TestAdminInviteResend:
    def test_resend_invite(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        client.post('/api/admin/auth/invite/', {
            'email': 'invited@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
        })
        user = User.objects.get(email='invited@example.com')
        old_otp_count = TwoFactorOTP.objects.filter(user=user, purpose='ACTION_CONFIRM').count()

        resp = client.post(f'/api/admin/auth/invite/{user.id}/resend/')
        assert resp.status_code == 200
        assert resp.json()['detail'] == 'Invite resent.'

        new_otp_count = TwoFactorOTP.objects.filter(user=user, purpose='ACTION_CONFIRM').count()
        assert new_otp_count == old_otp_count + 1

    def test_resend_revoked_invite_fails(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        client.post('/api/admin/auth/invite/', {
            'email': 'invited@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
        })
        user = User.objects.get(email='invited@example.com')
        client.post(f'/api/admin/auth/invite/{user.id}/revoke/', {'confirm': True})
        resp = client.post(f'/api/admin/auth/invite/{user.id}/resend/')
        assert resp.status_code == 400

    def test_resend_not_found(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        resp = client.post(f'/api/admin/auth/invite/{uuid.uuid4()}/resend/')
        assert resp.status_code == 404


class TestAdminInviteDuplicateEmail:
    def test_duplicate_email_returns_400(self, superuser):
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

    def test_duplicate_pending_invite_returns_400(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        client.post('/api/admin/auth/invite/', {
            'email': 'invited@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
        })
        # Same email while still PENDING
        resp = client.post('/api/admin/auth/invite/', {
            'email': 'invited@example.com',
            'first_name': 'Another',
            'last_name': 'User',
        })
        assert resp.status_code == 400

    def test_duplicate_email_existing_active_user_returns_400(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        User.objects.create_user(
            email='existing@example.com',
            phone_number='+254700000777',
            first_name='Existing',
            last_name='User',
            password='testpass123',
        )
        resp = client.post('/api/admin/auth/invite/', {
            'email': 'existing@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
        })
        assert resp.status_code == 400


class TestAdminInviteRevokeAccepted:
    def test_revoke_accepted_invite_returns_400(self, superuser):
        client = APIClient()
        client.force_authenticate(user=superuser)
        client.post('/api/admin/auth/invite/', {
            'email': 'invited@example.com',
            'first_name': 'Invited',
            'last_name': 'User',
        })
        user = User.objects.get(email='invited@example.com')
        user.is_active = True
        user.phone_number = '254700000111'
        user.save(update_fields=['is_active', 'phone_number'])
        resp = client.post(f'/api/admin/auth/invite/{user.id}/revoke/', {'confirm': True})
        assert resp.status_code == 400
        assert 'Cannot revoke an accepted invite' in resp.json()['detail']


class TestAdminCooperativeSerializer:
    def test_admin_put_allows_same_registration_number(self, superuser, cooperative):
        client = APIClient()
        client.force_authenticate(user=superuser)
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
            'prefix': cooperative.prefix or 'UPD',
        }
        resp = client.put(f'/api/admin/cooperatives/{cooperative.id}/', data, format='json')
        assert resp.status_code == 200
        assert resp.json()['registration_number'] == cooperative.registration_number

    def test_admin_put_rejects_duplicate_registration_number(self, superuser, cooperative):
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
        client = APIClient()
        client.force_authenticate(user=superuser)
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
            'prefix': cooperative.prefix or 'UPD',
        }
        resp = client.put(f'/api/admin/cooperatives/{cooperative.id}/', data, format='json')
        assert resp.status_code == 400
        assert resp.json()['registration_number'] == ['Cooperative with this registration number already exists.']
