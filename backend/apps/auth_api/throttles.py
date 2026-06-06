from django.core.signing import BadSignature, TimestampSigner
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle

from .serializers import FARMER_LOGIN_TOKEN_SALT, LOGIN_TOKEN_SALT


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
