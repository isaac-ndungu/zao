from rest_framework.routers import SimpleRouter
from apps.deliveries.views import DeliveryViewSet

router = SimpleRouter()
router.register('deliveries', DeliveryViewSet)

urlpatterns = router.urls
