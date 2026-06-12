from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken


def encrypt_field(value: str) -> str:
    if not value:
        return value
    f = Fernet(settings.FIELD_ENCRYPTION_KEY.encode())
    return f.encrypt(value.encode()).decode()


def decrypt_field(value: str) -> str:
    if not value:
        return value
    f = Fernet(settings.FIELD_ENCRYPTION_KEY.encode())
    try:
        return f.decrypt(value.encode()).decode()
    except InvalidToken:
        return value
