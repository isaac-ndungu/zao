from rest_framework.routers import SimpleRouter
from apps.inventory.views import InventoryViewSet, StockViewSet

router = SimpleRouter()
router.register('inventory', InventoryViewSet)
router.register('stock', StockViewSet)

urlpatterns = router.urls
