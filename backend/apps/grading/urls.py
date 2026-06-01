from rest_framework.routers import SimpleRouter
from apps.grading.views import GradeViewSet, GradeDisputeViewSet

router = SimpleRouter()
router.register('grades', GradeViewSet)
router.register('disputes', GradeDisputeViewSet)

urlpatterns = router.urls
