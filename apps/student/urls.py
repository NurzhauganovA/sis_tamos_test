from rest_framework.routers import DefaultRouter
from apps.student.views import StudentViewSet


router = DefaultRouter()
router.register("", StudentViewSet, basename='')


urlpatterns = router.urls
