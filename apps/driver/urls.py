from rest_framework.routers import DefaultRouter
from .views import RouteViewSet, TransportViewSet, DriverViewSet, HistoryDriverViewSet


router = DefaultRouter()


router.register("route", RouteViewSet, basename="route")
router.register("transport", TransportViewSet, basename="transport")
router.register("driver", DriverViewSet, basename="driver")
router.register("history", HistoryDriverViewSet, basename="history")


urlpatterns = router.urls
