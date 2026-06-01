from rest_framework.routers import DefaultRouter

from .views import DeductionViewSet, FarmInputCreditViewSet

router = DefaultRouter()
router.register('', DeductionViewSet, basename='deduction')
router.register('farm-input-credits', FarmInputCreditViewSet, basename='farm-input-credit')

urlpatterns = router.urls
