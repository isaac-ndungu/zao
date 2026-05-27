from django.conf import settings
from cryptography.fernet import Fernet


def encrypt_field(value: str) -> str:
    if not value:
        return value
    f = Fernet(settings.FIELD_ENCRYPTION_KEY.encode())
    return f.encrypt(value.encode()).decode()


def decrypt_field(value: str) -> str:
    if not value:
        return value
    f = Fernet(settings.FIELD_ENCRYPTION_KEY.encode())
    return f.decrypt(value.encode()).decode()
