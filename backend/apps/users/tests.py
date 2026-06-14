from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request as DRFRequest

from apps.auth_api.models import User
from apps.cooperatives.models import Cooperative
from apps.users.views import UserViewSet


class UserViewSetTestCase(TestCase):
    def setUp(self):
        self.coop_a = Cooperative.objects.create(name='A', registration_number='A1', county='C', produce_type='DAIRY', payment_model='FIXED_PRICE', levy_percentage=0, monthly_fee=0)
        self.coop_b = Cooperative.objects.create(name='B', registration_number='B1', county='C', produce_type='DAIRY', payment_model='FIXED_PRICE', levy_percentage=0, monthly_fee=0)

        # Admin (no cooperative)
        self.admin = User.objects.create_superuser(email='admin@example.com', phone_number='100', first_name='Admin', last_name='User', password='pass')

        # Manager in coop A
        self.manager = User.objects.create_user(email='mgr@example.com', phone_number='101', first_name='Mgr', last_name='User', password='pass', role='manager', cooperative=self.coop_a)

        # Users in various coops and roles
        User.objects.create_user(email='u1@a.com', phone_number='102', first_name='U1', last_name='A', password='pass', role='manager', cooperative=self.coop_a)
        User.objects.create_user(email='u2@a.com', phone_number='103', first_name='U2', last_name='A', password='pass', role='farmer', cooperative=self.coop_a)
        User.objects.create_user(email='u1@b.com', phone_number='104', first_name='U1', last_name='B', password='pass', role='manager', cooperative=self.coop_b)

    def _get_qs_for(self, user, params):
        factory = APIRequestFactory()
        django_req = factory.get('/api/users/', params)
        drf_req = DRFRequest(django_req)
        drf_req.user = user
        # ensure cooperative_id is set as the middleware would
        drf_req.cooperative_id = getattr(user.cooperative, 'id', None)
        view = UserViewSet()
        view.request = drf_req
        view.queryset = User.objects.all()
        return view.get_queryset()

    def test_manager_sees_only_own_cooperative_users_and_role_filter(self):
        qs = self._get_qs_for(self.manager, {'role': 'manager'})
        emails = set(qs.values_list('email', flat=True))
        # should include manager and u1@a.com but not u1@b.com or admin
        self.assertIn('mgr@example.com', emails)
        self.assertIn('u1@a.com', emails)
        self.assertNotIn('u1@b.com', emails)
        self.assertNotIn('admin@example.com', emails)

    def test_admin_sees_all_users_when_role_filter(self):
        qs = self._get_qs_for(self.admin, {'role': 'manager'})
        emails = set(qs.values_list('email', flat=True))
        # should include managers from both coops
        self.assertIn('u1@a.com', emails)
        self.assertIn('u1@b.com', emails)
import io
import tempfile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.auth_api.models import User


pytestmark = pytest.mark.django_db


def _png_file():
    buf = io.BytesIO()
    img = Image.new('RGB', (100, 100), color='red')
    img.save(buf, format='PNG')
    return SimpleUploadedFile('avatar.png', buf.getvalue(), content_type='image/png')


def _jpeg_file():
    buf = io.BytesIO()
    img = Image.new('RGB', (100, 100), color='blue')
    img.save(buf, format='JPEG')
    buf.seek(0)
    return SimpleUploadedFile('avatar.jpg', buf.getvalue(), content_type='image/jpeg')


def _txt_file():
    return SimpleUploadedFile('test.txt', b'not an image', content_type='text/plain')


class TestUserAvatar:
    def test_avatar_in_list_serializer(self, api_client):
        resp = api_client.get('/api/users/me/')
        assert resp.status_code == 200
        assert 'avatar' in resp.json()

    def test_upload_avatar(self, api_client):
        resp = api_client.patch('/api/users/avatar/', {'avatar': _png_file()}, format='multipart')
        assert resp.status_code == 200
        assert resp.json()['avatar'] is not None

    def test_upload_jpeg_avatar(self, api_client):
        resp = api_client.patch('/api/users/avatar/', {'avatar': _jpeg_file()}, format='multipart')
        assert resp.status_code == 200

    def test_reject_non_image(self, api_client):
        resp = api_client.patch('/api/users/avatar/', {'avatar': _txt_file()}, format='multipart')
        assert resp.status_code == 400

    def test_reject_oversized_avatar(self, api_client):
        buf = io.BytesIO()
        img = Image.new('RGB', (1000, 1000), color='green')
        img.save(buf, format='JPEG', quality=95)
        buf.seek(0)
        # Force a large size by extending the buffer
        large = buf.getvalue() + b'\x00' * (6 * 1024 * 1024)
        huge = SimpleUploadedFile('large.jpg', large, content_type='image/jpeg')
        resp = api_client.patch('/api/users/avatar/', {'avatar': huge}, format='multipart')
        assert resp.status_code == 400

    def test_delete_avatar(self, api_client):
        # Upload first
        api_client.patch('/api/users/avatar/', {'avatar': _png_file()}, format='multipart')
        resp = api_client.delete('/api/users/avatar/')
        assert resp.status_code == 204
        # Verify avatar is null
        resp = api_client.get('/api/users/me/')
        assert resp.json()['avatar'] is None

    def test_delete_avatar_when_none(self, api_client):
        resp = api_client.delete('/api/users/avatar/')
        assert resp.status_code == 204

    def test_avatar_requires_auth(self, client):
        resp = client.patch('/api/users/avatar/', {'avatar': _png_file()}, format='multipart')
        assert resp.status_code == 401

    def test_email_read_only_in_self_update(self, api_client):
        resp = api_client.patch('/api/users/me/', {'email': 'new@example.com'}, format='json')
        assert resp.status_code == 200
        assert resp.json()['email'] != 'new@example.com'
