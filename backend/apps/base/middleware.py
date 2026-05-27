class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.cooperative_id = (
            getattr(request.user, 'cooperative_id', None)
            if request.user.is_authenticated
            else None
        )
        return self.get_response(request)
