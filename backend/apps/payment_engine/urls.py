from rest_framework.routers import SimpleRouter
from apps.payment_engine.views import PaymentCycleViewSet

router = SimpleRouter()
router.register('payment-engine', PaymentCycleViewSet)

urlpatterns = router.urls