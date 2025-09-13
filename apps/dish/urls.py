from rest_framework.routers import DefaultRouter
from apps.dish.views import DishWeekViewSet, DishWeightNameViewSet


router = DefaultRouter()
router.register("weight", DishWeightNameViewSet, basename="dish_weight")
router.register("menu_week", DishWeekViewSet, basename="dish_week")


urlpatterns = router.urls
