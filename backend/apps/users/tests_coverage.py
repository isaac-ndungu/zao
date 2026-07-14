import io
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from apps.base.constants import UserRole
from apps.conftest import CooperativeFactory, UserFactory
from apps.users.serializers import (
    AvatarUploadSerializer,
    UserCreateSerializer,
    UserSelfUpdateSerializer,
    UserUpdateSerializer,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _png_file(size=100):
    buf = io.BytesIO()
    img = Image.new('RGB', (size, size), color='red')
    img.save(buf, format='PNG')
    return SimpleUploadedFile('avatar.png', buf.getvalue(), content_type='image/png')


def _jpeg_file(size=100):
    buf = io.BytesIO()
    img = Image.new('RGB', (size, size), color='blue')
    img.save(buf, format='JPEG')
    buf.seek(0)
    return SimpleUploadedFile('avatar.jpg', buf.getvalue(), content_type='image/jpeg')


def _txt_file():
    return SimpleUploadedFile('test.txt', b'not an image', content_type='text/plain')


def _oversized_jpeg():
    buf = io.BytesIO()
    img = Image.new('RGB', (100, 100), color='green')
    img.save(buf, format='JPEG', quality=95)
    buf.seek(0)
    large = buf.getvalue() + b'\x00' * (6 * 1024 * 1024)
    return SimpleUploadedFile('large.jpg', large, content_type='image/jpeg')


# =============================================================================
# UserCreateSerializer
# =============================================================================


class TestUserCreateSerializer:
    def test_create_with_explicit_password(self, db):
        data = {
            'email': 'new@example.com',
            'phone_number': '+254700000001',
            'first_name': 'New',
            'last_name': 'User',
            'role': UserRole.MANAGER,
            'password': 'mypassword123',
        }
        s = UserCreateSerializer(data=data)
        assert s.is_valid(), s.errors
        user = s.save()
        assert user.check_password('mypassword123')
        assert user.role == UserRole.MANAGER

    def test_create_without_password_auto_generates(self, db):
        data = {
            'email': 'autogen@example.com',
            'phone_number': '+254700000002',
            'first_name': 'Auto',
            'last_name': 'Gen',
            'role': UserRole.MANAGER,
        }
        s = UserCreateSerializer(data=data)
        assert s.is_valid(), s.errors
        with patch('apps.users.serializers.send_account_credentials') as mock_email:
            user = s.save()
        assert user.pk is not None
        assert user.has_usable_password()

    def test_email_case_insensitive_unique_check(self, db):
        UserFactory(email='existing@example.com', phone_number='+254700000010')
        data = {
            'email': 'EXISTING@EXAMPLE.COM',
            'phone_number': '+254700000003',
            'first_name': 'Dup',
            'last_name': 'Email',
            'role': UserRole.MANAGER,
        }
        s = UserCreateSerializer(data=data)
        assert not s.is_valid()
        assert 'email' in s.errors

    def test_email_is_lowercased(self, db):
        data = {
            'email': 'Mixed@Example.com',
            'phone_number': '+254700000004',
            'first_name': 'Mixed',
            'last_name': 'Case',
            'role': UserRole.MANAGER,
        }
        s = UserCreateSerializer(data=data)
        assert s.is_valid(), s.errors
        user = s.save()
        assert user.email == 'mixed@example.com'

    def test_phone_number_unique_check(self, db):
        UserFactory(phone_number='254700000005')
        data = {
            'email': 'another@example.com',
            'phone_number': '+254700000005',
            'first_name': 'Dup',
            'last_name': 'Phone',
            'role': UserRole.MANAGER,
        }
        s = UserCreateSerializer(data=data)
        assert not s.is_valid()
        assert 'phone_number' in s.errors

    def test_phone_number_is_normalized(self, db):
        data = {
            'email': 'norm@example.com',
            'phone_number': '0700000006',
            'first_name': 'Norm',
            'last_name': 'Phone',
            'role': UserRole.MANAGER,
        }
        s = UserCreateSerializer(data=data)
        assert s.is_valid(), s.errors
        user = s.save()
        assert user.phone_number == '254700000006'

    def test_must_change_password_true_for_non_admin_farmer_roles(self, db):
        for role in [UserRole.MANAGER, UserRole.ACCOUNTANT, UserRole.GRADER]:
            data = {
                'email': f'{role}@example.com',
                'phone_number': f'+25470000{ord(role[0]):04d}',
                'first_name': 'T',
                'last_name': 'User',
                'role': role,
            }
            s = UserCreateSerializer(data=data)
            assert s.is_valid(), s.errors
            user = s.save()
            assert user.must_change_password is True

    def test_must_change_password_false_for_admin(self, db):
        data = {
            'email': 'admincreate@example.com',
            'phone_number': '+254700000007',
            'first_name': 'A',
            'last_name': 'Admin',
            'role': UserRole.ADMIN,
        }
        s = UserCreateSerializer(data=data)
        assert s.is_valid(), s.errors
        user = s.save()
        assert user.must_change_password is False

    def test_must_change_password_false_for_farmer(self, db):
        data = {
            'email': 'farmercreate@example.com',
            'phone_number': '+254700000008',
            'first_name': 'F',
            'last_name': 'Farmer',
            'role': UserRole.FARMER,
        }
        s = UserCreateSerializer(data=data)
        assert s.is_valid(), s.errors
        user = s.save()
        assert user.must_change_password is False

    @patch('apps.users.serializers.send_account_credentials')
    def test_welcome_email_is_sent(self, mock_email, db):
        data = {
            'email': 'welcome@example.com',
            'phone_number': '+254700000009',
            'first_name': 'Welcome',
            'last_name': 'User',
            'role': UserRole.MANAGER,
        }
        s = UserCreateSerializer(data=data)
        assert s.is_valid(), s.errors
        s.save()
        mock_email.assert_called_once()


# =============================================================================
# UserUpdateSerializer
# =============================================================================


class TestUserUpdateSerializer:
    def test_update_basic_fields(self, db):
        user = UserFactory(email='upd@example.com', phone_number='+254700000100')
        s = UserUpdateSerializer(user, data={'first_name': 'Updated'}, partial=True)
        assert s.is_valid(), s.errors
        updated = s.save()
        assert updated.first_name == 'Updated'

    def test_email_unique_excludes_self(self, db):
        user = UserFactory(email='self@example.com', phone_number='+254700000101')
        s = UserUpdateSerializer(user, data={'email': 'self@example.com'}, partial=True)
        assert s.is_valid(), s.errors

    def test_email_unique_conflict(self, db):
        user1 = UserFactory(email='taken@example.com', phone_number='+254700000102')
        user2 = UserFactory(email='other@example.com', phone_number='+254700000103')
        s = UserUpdateSerializer(user2, data={'email': 'taken@example.com'}, partial=True)
        assert not s.is_valid()
        assert 'email' in s.errors

    def test_email_lowercased_on_update(self, db):
        user = UserFactory(email='lower@example.com', phone_number='+254700000104')
        s = UserUpdateSerializer(user, data={'email': 'UPPER@EXAMPLE.COM'}, partial=True)
        assert s.is_valid(), s.errors
        updated = s.save()
        assert updated.email == 'upper@example.com'

    def test_phone_unique_excludes_self(self, db):
        user = UserFactory(phone_number='+254700000105')
        s = UserUpdateSerializer(user, data={'phone_number': '+254700000105'}, partial=True)
        assert s.is_valid(), s.errors

    def test_phone_unique_conflict(self, db):
        user1 = UserFactory(phone_number='+254700000106')
        user2 = UserFactory(phone_number='+254700000107')
        s = UserUpdateSerializer(user2, data={'phone_number': '+254700000106'}, partial=True)
        assert not s.is_valid()
        assert 'phone_number' in s.errors

    def test_phone_normalized_on_update(self, db):
        user = UserFactory(phone_number='+254700000108')
        s = UserUpdateSerializer(user, data={'phone_number': '0700000109'}, partial=True)
        assert s.is_valid(), s.errors
        updated = s.save()
        assert updated.phone_number == '254700000109'

    def test_cooperative_id_valid(self, db):
        coop = CooperativeFactory()
        user = UserFactory(phone_number='+254700000110')
        s = UserUpdateSerializer(user, data={'cooperative_id': str(coop.id)}, partial=True)
        assert s.is_valid(), s.errors

    def test_cooperative_id_invalid(self, db):
        import uuid
        user = UserFactory(phone_number='+254700000111')
        s = UserUpdateSerializer(user, data={'cooperative_id': str(uuid.uuid4())}, partial=True)
        assert not s.is_valid()
        assert 'cooperative_id' in s.errors

    def test_password_clears_must_change_password(self, db):
        user = UserFactory(phone_number='+254700000112')
        user.must_change_password = True
        user.save()
        s = UserUpdateSerializer(user, data={'password': 'newpass123'}, partial=True)
        assert s.is_valid(), s.errors
        updated = s.save()
        assert updated.must_change_password is False
        assert updated.check_password('newpass123')

    def test_no_password_does_not_change_must_change_password(self, db):
        user = UserFactory(phone_number='+254700000113')
        user.must_change_password = True
        user.save()
        s = UserUpdateSerializer(user, data={'first_name': 'Still'}, partial=True)
        assert s.is_valid(), s.errors
        updated = s.save()
        assert updated.must_change_password is True


# =============================================================================
# UserSelfUpdateSerializer
# =============================================================================


class TestUserSelfUpdateSerializer:
    def test_update_first_name(self, db):
        user = UserFactory(phone_number='+254700000200')
        s = UserSelfUpdateSerializer(user, data={'first_name': 'Self'}, partial=True)
        assert s.is_valid(), s.errors
        updated = s.save()
        assert updated.first_name == 'Self'

    def test_email_is_read_only(self, db):
        user = UserFactory(email='readonly@example.com', phone_number='+254700000201')
        s = UserSelfUpdateSerializer(user, data={'email': 'hacked@example.com'}, partial=True)
        assert s.is_valid(), s.errors
        updated = s.save()
        assert updated.email == 'readonly@example.com'

    def test_valid_kenya_phone(self, db):
        user = UserFactory(phone_number='+254700000202')
        s = UserSelfUpdateSerializer(user, data={'phone_number': '+254700000203'}, partial=True)
        assert s.is_valid(), s.errors

    def test_invalid_kenya_phone_format(self, db):
        user = UserFactory(phone_number='+254700000204')
        s = UserSelfUpdateSerializer(user, data={'phone_number': '12345'}, partial=True)
        assert not s.is_valid()
        assert 'phone_number' in s.errors

    def test_phone_unique_excludes_self(self, db):
        user = UserFactory(phone_number='+254700000205')
        s = UserSelfUpdateSerializer(user, data={'phone_number': '+254700000205'}, partial=True)
        assert s.is_valid(), s.errors

    def test_phone_unique_conflict(self, db):
        user1 = UserFactory(phone_number='+254700000206')
        user2 = UserFactory(phone_number='+254700000207')
        s = UserSelfUpdateSerializer(user2, data={'phone_number': '+254700000206'}, partial=True)
        assert not s.is_valid()
        assert 'phone_number' in s.errors

    def test_password_requires_current_password(self, db):
        user = UserFactory(phone_number='+254700000208')
        s = UserSelfUpdateSerializer(user, data={'password': 'newpass'}, partial=True)
        assert not s.is_valid()
        assert 'current_password' in s.errors

    def test_current_password_wrong(self, db):
        user = UserFactory(phone_number='+254700000209')
        user.set_password('correctpass')
        user.save()
        s = UserSelfUpdateSerializer(
            user,
            data={'password': 'newpass', 'current_password': 'wrongpass'},
            partial=True,
        )
        assert not s.is_valid()
        assert 'current_password' in s.errors

    def test_password_change_with_correct_current(self, db):
        user = UserFactory(phone_number='+254700000210')
        user.set_password('oldpass')
        user.save()
        s = UserSelfUpdateSerializer(
            user,
            data={'password': 'newpass', 'current_password': 'oldpass'},
            partial=True,
        )
        assert s.is_valid(), s.errors
        updated = s.save()
        assert updated.check_password('newpass')
        assert updated.must_change_password is False

    def test_change_only_current_password_without_new_password(self, db):
        user = UserFactory(phone_number='+254700000211')
        user.set_password('mypass')
        user.save()
        s = UserSelfUpdateSerializer(
            user,
            data={'current_password': 'mypass'},
            partial=True,
        )
        assert s.is_valid(), s.errors

    def test_avatar_is_read_only(self, db):
        user = UserFactory(phone_number='+254700000212')
        s = UserSelfUpdateSerializer(user, data={'avatar': 'something'}, partial=True)
        assert s.is_valid(), s.errors
        updated = s.save()
        assert updated.avatar.name is None or updated.avatar.name == ''


# =============================================================================
# AvatarUploadSerializer
# =============================================================================


class TestAvatarUploadSerializer:
    def test_valid_png(self, db):
        s = AvatarUploadSerializer(data={'avatar': _png_file()})
        assert s.is_valid(), s.errors

    def test_valid_jpeg(self, db):
        s = AvatarUploadSerializer(data={'avatar': _jpeg_file()})
        assert s.is_valid(), s.errors

    def test_reject_txt_file(self, db):
        s = AvatarUploadSerializer(data={'avatar': _txt_file()})
        assert not s.is_valid()
        assert 'avatar' in s.errors

    def test_reject_oversized(self, db):
        s = AvatarUploadSerializer(data={'avatar': _oversized_jpeg()})
        assert not s.is_valid()
        assert 'avatar' in s.errors

    def test_reject_empty_file(self, db):
        empty = SimpleUploadedFile('empty.jpg', b'', content_type='image/jpeg')
        s = AvatarUploadSerializer(data={'avatar': empty})
        assert not s.is_valid()

    def test_reject_gif(self, db):
        buf = io.BytesIO()
        img = Image.new('RGB', (10, 10), color='yellow')
        img.save(buf, format='GIF')
        gif = SimpleUploadedFile('anim.gif', buf.getvalue(), content_type='image/gif')
        s = AvatarUploadSerializer(data={'avatar': gif})
        assert not s.is_valid()
        assert 'avatar' in s.errors


# =============================================================================
# UserViewSet — me action
# =============================================================================


class TestUserViewSetMe:
    URL = '/api/users/me/'

    def test_get_returns_profile(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data['email'] == api_client.user.email
        assert 'role' in data
        assert 'avatar' in data

    def test_patch_updates_name(self, api_client):
        resp = api_client.patch(self.URL, {'first_name': 'Patched'}, format='json')
        assert resp.status_code == 200
        assert resp.json()['first_name'] == 'Patched'

    def test_patch_phone(self, api_client):
        resp = api_client.patch(
            self.URL,
            {'phone_number': '+254700099999'},
            format='json',
        )
        assert resp.status_code == 200
        assert resp.json()['phone_number'] == '254700099999'

    def test_patch_invalid_phone_rejected(self, api_client):
        resp = api_client.patch(
            self.URL,
            {'phone_number': '12345'},
            format='json',
        )
        assert resp.status_code == 400

    def test_patch_email_ignored(self, api_client):
        original_email = api_client.user.email
        resp = api_client.patch(self.URL, {'email': 'new@example.com'}, format='json')
        assert resp.status_code == 200
        assert resp.json()['email'] == original_email

    def test_unauthenticated_me_returns_401(self):
        client = APIClient()
        resp = client.get(self.URL)
        assert resp.status_code == 401

    def test_password_change_via_me(self, api_client):
        api_client.user.set_password('oldpass')
        api_client.user.save()
        resp = api_client.patch(
            self.URL,
            {'password': 'newpass123', 'current_password': 'oldpass'},
            format='json',
        )
        assert resp.status_code == 200
        api_client.user.refresh_from_db()
        assert api_client.user.check_password('newpass123')

    def test_password_change_wrong_current(self, api_client):
        api_client.user.set_password('correct')
        api_client.user.save()
        resp = api_client.patch(
            self.URL,
            {'password': 'newpass', 'current_password': 'wrong'},
            format='json',
        )
        assert resp.status_code == 400


# =============================================================================
# UserViewSet — avatar action
# =============================================================================


class TestUserViewSetAvatar:
    URL = '/api/users/avatar/'

    def test_upload_avatar(self, api_client):
        resp = api_client.patch(self.URL, {'avatar': _png_file()}, format='multipart')
        assert resp.status_code == 200
        assert resp.json()['avatar'] is not None

    def test_upload_jpeg_avatar(self, api_client):
        resp = api_client.patch(self.URL, {'avatar': _jpeg_file()}, format='multipart')
        assert resp.status_code == 200

    def test_upload_replaces_old_avatar(self, api_client):
        api_client.patch(self.URL, {'avatar': _png_file()}, format='multipart')
        api_client.patch(self.URL, {'avatar': _jpeg_file()}, format='multipart')
        resp = api_client.get('/api/users/me/')
        assert resp.json()['avatar'] is not None

    def test_reject_non_image(self, api_client):
        resp = api_client.patch(self.URL, {'avatar': _txt_file()}, format='multipart')
        assert resp.status_code == 400

    def test_reject_oversized(self, api_client):
        resp = api_client.patch(self.URL, {'avatar': _oversized_jpeg()}, format='multipart')
        assert resp.status_code == 400

    def test_unauthenticated_returns_401(self):
        client = APIClient()
        resp = client.patch(self.URL, {'avatar': _png_file()}, format='multipart')
        assert resp.status_code == 401

    @patch('cloudinary.uploader.destroy')
    def test_old_avatar_cloudinary_destroy_called(self, mock_destroy, api_client):
        api_client.patch(self.URL, {'avatar': _png_file()}, format='multipart')
        api_client.patch(self.URL, {'avatar': _jpeg_file()}, format='multipart')
        assert mock_destroy.call_count >= 1

    @patch('cloudinary.uploader.destroy')
    def test_old_avatar_cloudinary_destroy_error_swallowed(self, mock_destroy, api_client):
        mock_destroy.side_effect = Exception('cloudinary down')
        api_client.patch(self.URL, {'avatar': _png_file()}, format='multipart')
        resp = api_client.patch(self.URL, {'avatar': _jpeg_file()}, format='multipart')
        assert resp.status_code == 200


# =============================================================================
# UserViewSet — delete_avatar action
# =============================================================================


class TestUserViewSetDeleteAvatar:
    URL = '/api/users/avatar/'

    def test_delete_avatar_when_present(self, api_client):
        api_client.patch(self.URL, {'avatar': _png_file()}, format='multipart')
        resp = api_client.delete(self.URL)
        assert resp.status_code == 204
        me = api_client.get('/api/users/me/').json()
        assert me['avatar'] is None

    def test_delete_avatar_when_none(self, api_client):
        resp = api_client.delete(self.URL)
        assert resp.status_code == 204

    def test_unauthenticated_returns_401(self):
        client = APIClient()
        resp = client.delete(self.URL)
        assert resp.status_code == 401

    @patch('cloudinary.uploader.destroy')
    def test_cloudinary_destroy_called(self, mock_destroy, api_client):
        api_client.patch(self.URL, {'avatar': _png_file()}, format='multipart')
        api_client.delete(self.URL)
        mock_destroy.assert_called()

    @patch('cloudinary.uploader.destroy')
    def test_cloudinary_error_swallowed(self, mock_destroy, api_client):
        mock_destroy.side_effect = Exception('fail')
        api_client.patch(self.URL, {'avatar': _png_file()}, format='multipart')
        resp = api_client.delete(self.URL)
        assert resp.status_code == 204
