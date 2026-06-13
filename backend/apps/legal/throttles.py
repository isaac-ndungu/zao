from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class _RateFallbackMixin:
    def get_rate(self):
        try:
            return self.THROTTLE_RATES[self.scope]
        except KeyError:
            return self.rate


class LegalDocumentAnonThrottle(_RateFallbackMixin, AnonRateThrottle):
    scope = 'legal_document'
    rate = '20/min'
