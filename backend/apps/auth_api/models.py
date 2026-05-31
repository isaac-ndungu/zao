import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.auth_api.managers import UserManager
from apps.base.constants import UserRole


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=UserRole.choices, null=True, blank=True)
    cooperative = models.ForeignKey(
        'cooperatives.Cooperative', on_delete=models.SET_NULL, null=True, blank=True
    )
    two_fa_enabled = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone_number', 'first_name', 'last_name']

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def get_short_name(self):
        return self.first_name

    def __str__(self):
        return self.email


class TwoFactorOTP(models.Model):
    PURPOSE_CHOICES = [
        ('LOGIN', 'Login'),
        ('PASSWORD_RESET', 'Password Reset'),
        ('ACTION_CONFIRM', 'Action Confirm'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_codes')
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Two-Factor OTP'
        verbose_name_plural = 'Two-Factor OTPs'

    def __str__(self):
        return f'{self.user.email} — {self.purpose} @ {self.created_at}'
