from rest_framework.routers import SimpleRouter
from apps.grading.views import GradeViewSet, GradeDisputeViewSet, GradePriceViewSet

router = SimpleRouter()
router.register('grades', GradeViewSet)
router.register('grade-prices', GradePriceViewSet)
router.register('disputes', GradeDisputeViewSet)

urlpatterns = router.urls
