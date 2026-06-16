from rest_framework.throttling import UserRateThrottle


class AnalyticsAdminThrottle(UserRateThrottle):
    scope = 'analytics_admin'


class AnalyticsStaffThrottle(UserRateThrottle):
    scope = 'analytics_staff'


class AnalyticsFarmerThrottle(UserRateThrottle):
    scope = 'analytics_farmer'


class AnalyticsExportThrottle(UserRateThrottle):
    scope = 'analytics_export'
