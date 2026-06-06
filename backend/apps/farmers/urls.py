from rest_framework.routers import SimpleRouter
from rest_framework_nested.routers import NestedSimpleRouter

from apps.farmers.views import FarmerViewSet, MembershipViewSet

router = SimpleRouter()
router.register('farmers', FarmerViewSet)

memberships_router = NestedSimpleRouter(router, 'farmers', lookup='farmer')
memberships_router.register('memberships', MembershipViewSet, basename='farmer-memberships')

urlpatterns = router.urls + memberships_router.urls
