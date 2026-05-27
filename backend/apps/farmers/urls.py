from rest_framework.routers import SimpleRouter
from apps.farmers.views import FarmerViewSet

router = SimpleRouter()
router.register('farmers', FarmerViewSet)

urlpatterns = router.urls
