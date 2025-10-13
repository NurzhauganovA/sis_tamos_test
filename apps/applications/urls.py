from rest_framework.routers import DefaultRouter
from .views import (
    ApplicationViewSet,
    ApplicationTypeViewSet,
    ServiceProviderViewSet,
    StudentApplicationViewSet,
    AccountApplicationServiceProvider, SchoolDataViewSet
)

router = DefaultRouter()
router.register('applications', ApplicationViewSet, basename='applications')
router.register('application-types', ApplicationTypeViewSet, basename='application-types')
router.register('service-providers', ServiceProviderViewSet, basename='service-providers')
router.register('my-students', StudentApplicationViewSet, basename='my-students')
router.register('account', AccountApplicationServiceProvider, basename='account')
router.register('school-data', SchoolDataViewSet, basename='school-data')

urlpatterns = router.urls