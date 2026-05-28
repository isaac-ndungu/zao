from rest_framework.routers import SimpleRouter
from apps.inventory.views import InventoryViewSet

router = SimpleRouter()
router.register('inventory', InventoryViewSet)

urlpatterns = router.urls
