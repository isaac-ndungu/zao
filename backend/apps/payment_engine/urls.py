from rest_framework.routers import SimpleRouter
from apps.payment_engine.views import FarmerPaymentViewSet, PaymentCycleViewSet

router = SimpleRouter()
router.register('payment-engine', PaymentCycleViewSet)

payments_router = SimpleRouter()
payments_router.register('payments', FarmerPaymentViewSet, basename='payment')

urlpatterns = router.urls + payments_router.urls