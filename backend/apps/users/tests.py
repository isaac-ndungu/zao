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
