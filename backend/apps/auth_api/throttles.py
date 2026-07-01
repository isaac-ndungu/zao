from django.core.signing import BadSignature, TimestampSigner
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle

from .serializers import (
    FARMER_LOGIN_TOKEN_SALT,
    INVITE_MAX_AGE_SECONDS,
    INVITE_TOKEN_SALT,
    LOGIN_TOKEN_SALT,
)


class _RateFallbackMixin:
    def get_rate(self):
        try:
            return self.THROTTLE_RATES[self.scope]
        except KeyError:
            return self.rate


class LoginRateThrottle(_RateFallbackMixin, AnonRateThrottle):
    scope = 'login'
    rate = '10/min'


class _UserFromTokenThrottle(_RateFallbackMixin, SimpleRateThrottle):
    scope = None
    rate = None

    def get_cache_key(self, request, view):
        login_token = None
        try:
            login_token = request.data.get('login_token')
        except Exception:
            pass

        if login_token:
            try:
                signer = TimestampSigner(salt=LOGIN_TOKEN_SALT)
                email = signer.unsign(login_token, max_age=180)
                return self.cache_format % {
                    'scope': self.scope,
                    'ident': f'user_{email}',
                }
            except BadSignature:
                pass

        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


class RequestOTPRateThrottle(_UserFromTokenThrottle):
    scope = 'request_otp'
    rate = '5/hour'


class VerifyOTPRateThrottle(_UserFromTokenThrottle):
    scope = 'verify_otp'
    rate = '5/min'


class _FarmerFromPhoneThrottle(_RateFallbackMixin, SimpleRateThrottle):
    scope = None
    rate = None

    def get_cache_key(self, request, view):
        phone = None
        try:
            phone = request.data.get('phone_number', '').strip()
        except Exception:
            pass
        if phone:
            return self.cache_format % {
                'scope': self.scope,
                'ident': f'phone_{phone}',
            }
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


class FarmerRequestOTPRateThrottle(_FarmerFromPhoneThrottle):
    scope = 'farmer_request_otp'
    rate = '3/hour'


class PasswordResetRateThrottle(_RateFallbackMixin, AnonRateThrottle):
    scope = 'password_reset'
    rate = '5/hour'

    def get_cache_key(self, request, view):
        email = None
        try:
            email = request.data.get('email', '').strip().lower()
        except Exception:
            pass
        if email:
            return self.cache_format % {
                'scope': self.scope,
                'ident': f'email_{email}',
            }
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


class PasswordResetVerifyRateThrottle(_RateFallbackMixin, AnonRateThrottle):
    scope = 'password_reset_verify'
    rate = '10/min'


class _TokenFromRequestBodyThrottle(_RateFallbackMixin, SimpleRateThrottle):
    scope = None
    rate = None
    token_field = 'token'
    token_salt = None

    def get_cache_key(self, request, view):
        token = None
        try:
            token = request.data.get(self.token_field)
        except Exception:
            pass
        if token:
            try:
                signer = TimestampSigner(salt=self.token_salt)
                email = signer.unsign(token, max_age=INVITE_MAX_AGE_SECONDS)
                return self.cache_format % {
                    'scope': self.scope,
                    'ident': f'user_{email}',
                }
            except BadSignature:
                pass
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


class InviteRequestOTPRateThrottle(_TokenFromRequestBodyThrottle):
    scope = 'invite_request_otp'
    rate = '3/hour'
    token_field = 'invite_token'
    token_salt = INVITE_TOKEN_SALT


class InviteVerifyRateThrottle(_TokenFromRequestBodyThrottle):
    scope = 'invite_verify'
    rate = '10/min'
    token_field = 'invite_token'
    token_salt = INVITE_TOKEN_SALT


class GoogleLoginRateThrottle(_RateFallbackMixin, AnonRateThrottle):
    scope = 'google_login'
    rate = '5/min'
