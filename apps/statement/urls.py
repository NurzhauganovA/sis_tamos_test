from rest_framework.routers import DefaultRouter
from apps.statement.views import StatementViewSet


router = DefaultRouter()
router.register("", StatementViewSet, basename='')


urlpatterns = router.urls
