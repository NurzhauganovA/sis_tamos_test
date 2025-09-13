from rest_framework.routers import DefaultRouter
from .views import IntegrationPaymentViewSet, Migration


router = DefaultRouter()
router.register('kaspi', IntegrationPaymentViewSet, basename='kaspi')
router.register("migration", Migration, basename="migration")

urlpatterns = router.urls
