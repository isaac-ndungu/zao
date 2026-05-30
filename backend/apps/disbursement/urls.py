from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import DisbursementViewSet

router = SimpleRouter()
router.register('', DisbursementViewSet, basename='disbursement')

urlpatterns = router.urls
