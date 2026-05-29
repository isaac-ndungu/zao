from rest_framework.routers import SimpleRouter
from apps.sales.views import BuyerViewSet, PaymentCycleViewSet, SaleViewSet

router = SimpleRouter()
router.register('buyers', BuyerViewSet)
router.register('payment-cycles', PaymentCycleViewSet)
router.register('sales', SaleViewSet)

urlpatterns = router.urls
