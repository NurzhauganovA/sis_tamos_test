from rest_framework.routers import DefaultRouter
from .views import SchoolView, ClassViewSet, SchoolRequisitesView


router = DefaultRouter()
router.register("school", SchoolView, basename="school")
router.register("requisites", SchoolRequisitesView, basename="requisites")
router.register("class", ClassViewSet, basename='class')


urlpatterns = router.urls
