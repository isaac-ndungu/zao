from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.routes.proxy import RouteProxyView
from apps.routes.views import RouteViewSet

router = SimpleRouter()
router.register('routes', RouteViewSet)

# NOTE: the proxy path must come before the router URLs so it isn't
# shadowed by the viewset's `routes/{pk}/` lookup.
urlpatterns = [
    path('routes/route/', RouteProxyView.as_view(), name='route-ors-proxy'),
] + router.urls
