from rest_framework.routers import SimpleRouter
from apps.grading.views import GradeViewSet

router = SimpleRouter()
router.register('grades', GradeViewSet)

urlpatterns = router.urls
