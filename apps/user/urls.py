from rest_framework.routers import DefaultRouter
from apps.user.views import UserRoleView, UserView, AdditionalParentView, UserInfoView, UserProfileView


router = DefaultRouter()
router.register("role", UserRoleView, basename="role")
router.register("user", UserView, basename="user")
router.register("user_info", UserInfoView, basename="user_info")
router.register("additional_parent", AdditionalParentView, basename="additional_parent")
router.register("my_profile", UserProfileView, basename="my_profile")

urlpatterns = router.urls
