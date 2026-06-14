import uuid
import secrets
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.auth_api.managers import UserManager
from apps.auth_api.models import OTPPurpose, TwoFactorOTP
from apps.base.constants import UserRole

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestUserManager:
    def test_create_user(self):
        user = User.objects.create_user(
            email='test@example.com',
            phone_number='+254700000001',
            first_name='Test',
            last_name='User',
            password='testpass123',
        )
        assert user.email == 'test@example.com'
        assert user.check_password('testpass123')
        assert not user.is_staff
        assert not user.is_superuser

    def test_create_user_requires_email(self):
        with pytest.raises(ValueError, match='Email is required'):
            User.objects.create_user(
                email='',
                phone_number='+254700000001',
                first_name='Test',
                last_name='User',
            )

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email='admin@example.com',
            phone_number='+254700000002',
            first_name='Admin',
            last_name='User',
            password='adminpass123',
        )
        assert user.is_staff
        assert user.is_superuser
        assert user.role == UserRole.ADMIN

    def test_default_manager_excludes_deleted(self):
        user = User.objects.create_user(
            email='del@example.com',
            phone_number='+254700000003',
            first_name='Del',
            last_name='User',
        )
        user.soft_delete()
        assert not User.objects.filter(pk=user.pk).exists()

    def test_all_with_trashed_includes_deleted(self):
        user = User.objects.create_user(
            email='trash@example.com',
            phone_number='+254700000004',
            first_name='Trash',
            last_name='User',
        )
        user.soft_delete()
        assert User.objects.all_with_trashed().filter(pk=user.pk).exists()

    def test_trashed_only(self):
        user = User.objects.create_user(
            email='trashonly@example.com',
            phone_number='+254700000005',
            first_name='Trash',
            last_name='Only',
        )
        assert not User.objects.trashed_only().filter(pk=user.pk).exists()
        user.soft_delete()
        assert User.objects.trashed_only().filter(pk=user.pk).exists()


class TestUserModel:
    def test_str(self):
        user = User.objects.create_user(
            email='str@example.com',
            phone_number='+254700000006',
            first_name='Str',
            last_name='Test',
        )
        assert str(user) == 'str@example.com'

    def test_get_full_name(self):
        user = User.objects.create_user(
            email='name@example.com',
            phone_number='+254700000007',
            first_name='John',
            last_name='Doe',
        )
        assert user.get_full_name() == 'John Doe'

    def test_get_short_name(self):
        user = User.objects.create_user(
            email='short@example.com',
            phone_number='+254700000008',
            first_name='Jane',
            last_name='Doe',
        )
        assert user.get_short_name() == 'Jane'

    def test_superuser_cannot_be_deleted(self, superuser):
        with pytest.raises(ValueError, match='Cannot delete a superuser'):
            superuser.delete()

    def test_superuser_can_be_soft_deleted(self):
        user = User.objects.create_superuser(
            email='su@example.com',
            phone_number='+254700000009',
            first_name='Su',
            last_name='User',
        )
        user.soft_delete()
        assert user.deleted_at is not None

    def test_hard_delete(self):
        user = User.objects.create_user(
            email='harddel@example.com',
            phone_number='+254700000010',
            first_name='Hard',
            last_name='Del',
        )
        user.hard_delete()
        assert not User.objects.all_with_trashed().filter(pk=user.pk).exists()

    def test_soft_delete_via_delete_method(self):
        user = User.objects.create_user(
            email='delmethod@example.com',
            phone_number='+254700000011',
            first_name='Del',
            last_name='Method',
        )
        user.delete()
        assert user.deleted_at is not None
        assert not User.objects.filter(pk=user.pk).exists()

    def test_fields(self, superuser):
        assert superuser.USERNAME_FIELD == 'email'
        assert User.REQUIRED_FIELDS == ['phone_number', 'first_name', 'last_name']
        assert superuser.email
        assert superuser.phone_number


class TestTwoFactorOTP:
    def test_create_otp(self, superuser):
        otp = TwoFactorOTP.objects.create(
            user=superuser,
            otp_code='654321',
            purpose=OTPPurpose.LOGIN,
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        assert otp.pk is not None

    def test_otp_str(self, superuser):
        otp = TwoFactorOTP.objects.create(
            user=superuser,
            otp_code='111111',
            purpose=OTPPurpose.LOGIN,
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        assert superuser.email in str(otp)
        assert 'LOGIN' in str(otp)

    def test_otp_default_attempts(self, superuser):
        otp = TwoFactorOTP.objects.create(
            user=superuser,
            otp_code='000000',
            purpose=OTPPurpose.PASSWORD_RESET,
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        assert otp.attempts == 0
        assert not otp.is_used

    def test_otp_purposes(self, superuser):
        for purpose in OTPPurpose.values:
            otp = TwoFactorOTP.objects.create(
                user=superuser,
                otp_code='123456',
                purpose=purpose,
                expires_at=timezone.now() + timedelta(minutes=5),
            )
            assert otp.purpose == purpose


class TestPasswordReset:
    def test_request_reset_unknown_email(self, client):
        resp = client.post('/api/auth/password-reset/request/', {'email': 'unknown@example.com'})
        assert resp.status_code == 400

    def test_request_reset_known_email(self, client, superuser):
        resp = client.post('/api/auth/password-reset/request/', {'email': superuser.email})
        assert resp.status_code == 200
        data = resp.json()
        assert 'reset_token' in data
        assert data['detail'] == 'OTP sent to your email.'

    def test_request_reset_creates_otp(self, client, superuser):
        client.post('/api/auth/password-reset/request/', {'email': superuser.email})
        otp = TwoFactorOTP.objects.filter(user=superuser, purpose='PASSWORD_RESET').first()
        assert otp is not None
        assert otp.expires_at > timezone.now()
        assert not otp.is_used

    def _get_otp(self, user):
        return TwoFactorOTP.objects.filter(
            user=user, purpose='PASSWORD_RESET'
        ).order_by('-created_at').first().otp_code

    def test_reset_with_valid_otp(self, client, superuser):
        client.post('/api/auth/password-reset/request/', {'email': superuser.email})
        otp_code = self._get_otp(superuser)
        # Manually create a reset token
        from django.core.signing import TimestampSigner
        from apps.auth_api.serializers import PASSWORD_RESET_TOKEN_SALT
        signer = TimestampSigner(salt=PASSWORD_RESET_TOKEN_SALT)
        reset_token = signer.sign(superuser.email)

        resp = client.post('/api/auth/password-reset/verify/', {
            'reset_token': reset_token,
            'otp_code': otp_code,
            'password': 'newpass123',
        })
        assert resp.status_code == 200
        assert resp.json()['detail'] == 'Password reset successful.'

        # User can login with new password
        from rest_framework.test import APIClient
        login_resp = APIClient().post('/api/auth/login/', {
            'email': superuser.email,
            'password': 'newpass123',
        })
        assert login_resp.status_code == 200

    def test_reset_with_wrong_otp(self, client, superuser):
        client.post('/api/auth/password-reset/request/', {'email': superuser.email})
        from django.core.signing import TimestampSigner
        from apps.auth_api.serializers import PASSWORD_RESET_TOKEN_SALT
        signer = TimestampSigner(salt=PASSWORD_RESET_TOKEN_SALT)
        reset_token = signer.sign(superuser.email)

        resp = client.post('/api/auth/password-reset/verify/', {
            'reset_token': reset_token,
            'otp_code': '000000',
            'password': 'newpass123',
        })
        assert resp.status_code == 400

    def test_reset_with_expired_otp(self, client, superuser):
        from datetime import timedelta
        TwoFactorOTP.objects.create(
            user=superuser,
            otp_code='123456',
            purpose='PASSWORD_RESET',
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        from django.core.signing import TimestampSigner
        from apps.auth_api.serializers import PASSWORD_RESET_TOKEN_SALT
        signer = TimestampSigner(salt=PASSWORD_RESET_TOKEN_SALT)
        reset_token = signer.sign(superuser.email)

        resp = client.post('/api/auth/password-reset/verify/', {
            'reset_token': reset_token,
            'otp_code': '123456',
            'password': 'newpass123',
        })
        assert resp.status_code == 400

    def test_reset_with_bad_token(self, client, superuser):
        resp = client.post('/api/auth/password-reset/verify/', {
            'reset_token': 'bad-token',
            'otp_code': '123456',
            'password': 'newpass123',
        })
        assert resp.status_code == 400

    def test_reset_rejects_short_password(self, client, superuser):
        client.post('/api/auth/password-reset/request/', {'email': superuser.email})
        otp_code = self._get_otp(superuser)
        from django.core.signing import TimestampSigner
        from apps.auth_api.serializers import PASSWORD_RESET_TOKEN_SALT
        signer = TimestampSigner(salt=PASSWORD_RESET_TOKEN_SALT)
        reset_token = signer.sign(superuser.email)

        resp = client.post('/api/auth/password-reset/verify/', {
            'reset_token': reset_token,
            'otp_code': otp_code,
            'password': 'short',
        })
        assert resp.status_code == 400

    def test_reset_otp_exhausted_attempts(self, client, superuser):
        from datetime import timedelta
        from django.core.signing import TimestampSigner
        from apps.auth_api.serializers import PASSWORD_RESET_TOKEN_SALT

        TwoFactorOTP.objects.create(
            user=superuser,
            otp_code='123456',
            purpose='PASSWORD_RESET',
            expires_at=timezone.now() + timedelta(minutes=5),
            attempts=5,
        )
        signer = TimestampSigner(salt=PASSWORD_RESET_TOKEN_SALT)
        reset_token = signer.sign(superuser.email)

        resp = client.post('/api/auth/password-reset/verify/', {
            'reset_token': reset_token,
            'otp_code': '123456',
            'password': 'newpass123',
        })
        assert resp.status_code == 400
        data = resp.json()
        assert any('Too many attempts' in str(v) for v in data.values())

    def test_reset_requires_auth_not_needed(self, client, superuser):
        resp = client.post('/api/auth/password-reset/request/', {'email': superuser.email})
        assert resp.status_code != 401


class Test2FASelfService:
    def test_enable_2fa(self, api_client):
        resp = api_client.post('/api/auth/2fa/enable/', {'password': api_client.user.raw_password})
        assert resp.status_code == 200
        assert resp.json()['detail'] == 'Two-factor authentication enabled.'
        api_client.user.refresh_from_db()
        assert api_client.user.two_fa_enabled is True

    def test_enable_2fa_wrong_password(self, api_client):
        resp = api_client.post('/api/auth/2fa/enable/', {'password': 'wrongpassword'})
        assert resp.status_code == 400

    def test_enable_2fa_already_enabled(self, api_client):
        api_client.user.two_fa_enabled = True
        api_client.user.save(update_fields=['two_fa_enabled'])
        resp = api_client.post('/api/auth/2fa/enable/', {'password': api_client.user.raw_password})
        assert resp.status_code == 400
        assert resp.json()['detail'] == '2FA is already enabled.'

    def test_enable_2fa_requires_auth(self, client):
        resp = client.post('/api/auth/2fa/enable/', {'password': 'testpass123'})
        assert resp.status_code == 401

    def test_disable_2fa(self, api_client):
        api_client.user.two_fa_enabled = True
        api_client.user.save(update_fields=['two_fa_enabled'])
        resp = api_client.post('/api/auth/2fa/disable/', {'password': api_client.user.raw_password})
        assert resp.status_code == 200
        assert resp.json()['detail'] == 'Two-factor authentication disabled.'
        api_client.user.refresh_from_db()
        assert api_client.user.two_fa_enabled is False

    def test_disable_2fa_not_enabled(self, api_client):
        resp = api_client.post('/api/auth/2fa/disable/', {'password': api_client.user.raw_password})
        assert resp.status_code == 400
        assert resp.json()['detail'] == '2FA is not enabled.'


class TestChangePassword:
    def test_change_password_success(self, api_client):
        old_password = api_client.user.raw_password
        resp = api_client.post('/api/auth/change-password/', {
            'current_password': old_password,
            'new_password': 'newpass1234',
        })
        assert resp.status_code == 200
        assert 'access' in resp.json()
        api_client.user.refresh_from_db()
        assert api_client.user.check_password('newpass1234')
        assert api_client.user.must_change_password is False

    def test_change_password_wrong_current(self, api_client):
        resp = api_client.post('/api/auth/change-password/', {
            'current_password': 'wrongpassword',
            'new_password': 'newpass1234',
        })
        assert resp.status_code == 400

    def test_change_password_short_new(self, api_client):
        resp = api_client.post('/api/auth/change-password/', {
            'current_password': api_client.user.raw_password,
            'new_password': 'short',
        })
        assert resp.status_code == 400

    def test_change_password_clears_flag(self, api_client):
        api_client.user.must_change_password = True
        api_client.user.save(update_fields=['must_change_password'])
        resp = api_client.post('/api/auth/change-password/', {
            'current_password': api_client.user.raw_password,
            'new_password': 'newpass1234',
        })
        assert resp.status_code == 200
        api_client.user.refresh_from_db()
        assert api_client.user.must_change_password is False

    def test_change_password_requires_auth(self, client):
        resp = client.post('/api/auth/change-password/', {
            'current_password': 'anything',
            'new_password': 'newpass1234',
        })
        assert resp.status_code == 401

    def test_login_blocked_when_must_change_password(self, client):
        user = User.objects.create_user(
            email='changeme@example.com',
            phone_number='+254700000999',
            first_name='Must',
            last_name='Change',
            password='testpass123',
            must_change_password=True,
        )
        resp = client.post('/api/auth/login/', {
            'email': 'changeme@example.com',
            'password': 'testpass123',
        })
        assert resp.status_code == 403
        data = resp.json()
        assert data['must_change_password'] is True

    def test_login_allows_after_password_change(self, client):
        user = User.objects.create_user(
            email='changed@example.com',
            phone_number='+254700000998',
            first_name='Already',
            last_name='Changed',
            password='testpass123',
            must_change_password=False,
        )
        resp = client.post('/api/auth/login/', {
            'email': 'changed@example.com',
            'password': 'testpass123',
        })
        assert resp.status_code == 200
        assert 'access' in resp.json()


class TestInvite:
    def _create_invite(self, **overrides):
        email = overrides.get('email', 'invited@example.com')
        user = User.objects.create(
            email=email,
            phone_number=f'pending-{uuid.uuid4().hex[:8]}',
            first_name=overrides.get('first_name', 'Invited'),
            last_name=overrides.get('last_name', 'User'),
            role='manager',
            is_active=False,
            must_change_password=True,
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])
        otp_code = f'{secrets.randbelow(1_000_000):06d}'
        TwoFactorOTP.objects.create(
            user=user,
            otp_code=otp_code,
            purpose='ACTION_CONFIRM',
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        return user, otp_code

    def test_invite_verify_valid_otp(self, api_client):
        user, otp_code = self._create_invite()

        from django.core.signing import TimestampSigner
        from apps.auth_api.serializers import INVITE_TOKEN_SALT
        signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
        invite_token = signer.sign(user.email)

        resp = api_client.post('/api/auth/invite/verify/', {
            'invite_token': invite_token,
            'otp_code': otp_code,
            'password': 'newpass123',
            'phone_number': '+254700000050',
        })
        assert resp.status_code == 200
        assert 'access' in resp.json()

        user.refresh_from_db()
        assert user.is_active is True
        assert user.must_change_password is False
        assert user.phone_number == '254700000050'
        assert user.check_password('newpass123')

    def test_invite_verify_wrong_otp(self, api_client):
        user, _ = self._create_invite()

        from django.core.signing import TimestampSigner
        from apps.auth_api.serializers import INVITE_TOKEN_SALT
        signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
        invite_token = signer.sign(user.email)

        resp = api_client.post('/api/auth/invite/verify/', {
            'invite_token': invite_token,
            'otp_code': '000000',
            'password': 'newpass123',
            'phone_number': '+254700000051',
        })
        assert resp.status_code == 400

    def test_invite_verify_expired_otp(self, api_client):
        user, _ = self._create_invite()

        # Create expired OTP
        TwoFactorOTP.objects.create(
            user=user,
            otp_code='654321',
            purpose='ACTION_CONFIRM',
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        from django.core.signing import TimestampSigner
        from apps.auth_api.serializers import INVITE_TOKEN_SALT
        signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
        invite_token = signer.sign(user.email)

        resp = api_client.post('/api/auth/invite/verify/', {
            'invite_token': invite_token,
            'otp_code': '654321',
            'password': 'newpass123',
            'phone_number': '+254700000052',
        })
        assert resp.status_code == 400

    def test_invite_verify_bad_token(self, api_client):
        resp = api_client.post('/api/auth/invite/verify/', {
            'invite_token': 'bad-token',
            'otp_code': '123456',
            'password': 'newpass123',
            'phone_number': '+254700000053',
        })
        assert resp.status_code == 400

    def test_invite_verify_short_password(self, api_client):
        user, otp_code = self._create_invite()

        from django.core.signing import TimestampSigner
        from apps.auth_api.serializers import INVITE_TOKEN_SALT
        signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
        invite_token = signer.sign(user.email)

        resp = api_client.post('/api/auth/invite/verify/', {
            'invite_token': invite_token,
            'otp_code': otp_code,
            'password': 'short',
            'phone_number': '+254700000054',
        })
        assert resp.status_code == 400

    def test_invite_verify_duplicate_phone(self, api_client):
        User.objects.create_user(
            email='existing@example.com',
            phone_number='254700000099',
            first_name='Existing',
            last_name='User',
            password='testpass123',
        )

        user, otp_code = self._create_invite()

        from django.core.signing import TimestampSigner
        from apps.auth_api.serializers import INVITE_TOKEN_SALT
        signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
        invite_token = signer.sign(user.email)

        resp = api_client.post('/api/auth/invite/verify/', {
            'invite_token': invite_token,
            'otp_code': otp_code,
            'password': 'newpass123',
            'phone_number': '254700000099',
        })
        assert resp.status_code == 400

    def test_invite_verify_exhausted_attempts(self, api_client):
        user, _ = self._create_invite()

        TwoFactorOTP.objects.create(
            user=user,
            otp_code='123456',
            purpose='ACTION_CONFIRM',
            expires_at=timezone.now() + timedelta(minutes=5),
            attempts=5,
        )

        from django.core.signing import TimestampSigner
        from apps.auth_api.serializers import INVITE_TOKEN_SALT
        signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
        invite_token = signer.sign(user.email)

        resp = api_client.post('/api/auth/invite/verify/', {
            'invite_token': invite_token,
            'otp_code': '123456',
            'password': 'newpass123',
            'phone_number': '+254700000055',
        })
        assert resp.status_code == 400
        data = resp.json()
        assert any('Too many attempts' in str(v) for v in data.values())

    def test_invite_verify_revoked(self, api_client):
        user, otp_code = self._create_invite()
        user.invite_revoked = True
        user.save(update_fields=['invite_revoked'])

        from django.core.signing import TimestampSigner
        from apps.auth_api.serializers import INVITE_TOKEN_SALT
        signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
        invite_token = signer.sign(user.email)

        resp = api_client.post('/api/auth/invite/verify/', {
            'invite_token': invite_token,
            'otp_code': otp_code,
            'password': 'newpass123',
            'phone_number': '+254700000057',
        })
        assert resp.status_code == 400

    def test_invite_request_otp_revoked(self, api_client):
        user, _ = self._create_invite()
        user.invite_revoked = True
        user.save(update_fields=['invite_revoked'])

        from django.core.signing import TimestampSigner
        from apps.auth_api.serializers import INVITE_TOKEN_SALT
        signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
        invite_token = signer.sign(user.email)

        resp = api_client.post('/api/auth/invite/request-otp/', {
            'invite_token': invite_token,
        })
        assert resp.status_code == 400

    def test_invite_request_otp_resend(self, api_client):
        user, _ = self._create_invite()

        from django.core.signing import TimestampSigner
        from apps.auth_api.serializers import INVITE_TOKEN_SALT
        signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
        invite_token = signer.sign(user.email)

        resp = api_client.post('/api/auth/invite/request-otp/', {
            'invite_token': invite_token,
        })
        assert resp.status_code == 200

        # A new OTP should have been created
        otps = TwoFactorOTP.objects.filter(user=user, purpose='ACTION_CONFIRM')
        assert otps.count() >= 2

    def test_invite_verify_no_auth_needed(self, client, api_client):
        user, otp_code = self._create_invite()

        from django.core.signing import TimestampSigner
        from apps.auth_api.serializers import INVITE_TOKEN_SALT
        signer = TimestampSigner(salt=INVITE_TOKEN_SALT)
        invite_token = signer.sign(user.email)

        # Unauthenticated client should be able to verify
        resp = client.post('/api/auth/invite/verify/', {
            'invite_token': invite_token,
            'otp_code': otp_code,
            'password': 'newpass123',
            'phone_number': '+254700000056',
        })
        assert resp.status_code == 200
        assert 'access' in resp.json()
