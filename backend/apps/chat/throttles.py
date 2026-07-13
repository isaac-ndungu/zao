from rest_framework.throttling import SimpleRateThrottle


class ChatRateThrottle(SimpleRateThrottle):
    scope = 'chat'
    rate = '30/hour'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return self.cache_format % {
                'scope': self.scope,
                'ident': f'user_{request.user.pk}',
            }
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }
