from rest_framework.routers import DefaultRouter

from .views import DeductionViewSet

router = DefaultRouter()
router.register('', DeductionViewSet, basename='deduction')

urlpatterns = router.urls
