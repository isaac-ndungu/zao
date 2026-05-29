from rest_framework.routers import SimpleRouter
from apps.routes.views import RouteViewSet

router = SimpleRouter()
router.register('routes', RouteViewSet)

urlpatterns = router.urls
