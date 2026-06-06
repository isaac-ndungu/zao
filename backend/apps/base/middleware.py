from django.conf import settings

from apps.farmers.models import Farmer


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            user_role = getattr(request.user, 'role', None)
            if user_role == 'farmer':
                coop_id = request.META.get('HTTP_X_COOPERATIVE_ID', '')
                if coop_id:
                    farmer = getattr(request.user, 'farmer_profile', None)
                    if farmer and farmer.memberships.filter(
                        cooperative_id=coop_id, is_active=True
                    ).exists():
                        request.cooperative_id = coop_id
                    else:
                        request.cooperative_id = getattr(request.user, 'cooperative_id', None)
                else:
                    farmer = getattr(request.user, 'farmer_profile', None)
                    if farmer:
                        active_memberships = list(
                            farmer.memberships.filter(is_active=True)
                        )
                        if len(active_memberships) == 1:
                            request.cooperative_id = active_memberships[0].cooperative_id
                        else:
                            request.cooperative_id = getattr(request.user, 'cooperative_id', None)
                    else:
                        request.cooperative_id = getattr(request.user, 'cooperative_id', None)
            else:
                request.cooperative_id = getattr(request.user, 'cooperative_id', None)
        else:
            request.cooperative_id = None
        return self.get_response(request)
