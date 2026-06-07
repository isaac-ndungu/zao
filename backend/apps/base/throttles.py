from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class GlobalUserRateThrottle(UserRateThrottle):
    rate = '1000/hour'


class GlobalAnonRateThrottle(AnonRateThrottle):
    rate = '100/hour'
