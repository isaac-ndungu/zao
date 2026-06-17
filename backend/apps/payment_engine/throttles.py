from rest_framework.throttling import UserRateThrottle


class PaymentExportThrottle(UserRateThrottle):
    scope = 'payment_export'
