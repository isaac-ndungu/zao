from django.conf import settings
from django.http import Http404


class SuperAdminIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        allowed_ips = settings.SUPERADMIN_ALLOWED_IPS
        if allowed_ips and request.path.startswith('/api/admin/'):
            remote_ip = request.META.get('REMOTE_ADDR', '')
            if remote_ip not in allowed_ips:
                raise Http404()
        return self.get_response(request)
