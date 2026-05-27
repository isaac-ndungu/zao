from rest_framework.routers import SimpleRouter
from apps.cooperatives.views import CooperativeViewSet

router = SimpleRouter()
router.register('cooperatives', CooperativeViewSet)

urlpatterns = router.urls
