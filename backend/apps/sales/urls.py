from rest_framework.routers import SimpleRouter
from apps.sales.views import BuyerViewSet, SaleViewSet

router = SimpleRouter()
router.register('buyers', BuyerViewSet)
router.register('sales', SaleViewSet)

urlpatterns = router.urls