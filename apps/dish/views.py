from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from .models import DishWeightName, DishWeek
from .serializers.dish_week import DishWeightNameSerializer, DishWeekSerializer

from .services import DishListService
from .services import DishWeekService
from .services import DishCreateService


class DishWeightNameViewSet(ModelViewSet):
    """ API для работы с весами блюд """

    queryset = DishWeightName.objects.all()
    serializer_class = DishWeightNameSerializer
    http_method_names = ['get', 'post', 'put']


class DishWeekViewSet(ModelViewSet):
    """ API для работы с блюдами недели """

    queryset = DishWeek.objects.all()
    serializer_class = DishWeekSerializer
    http_method_names = ['get', 'post', 'put']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dish_list_service = DishListService(self.queryset)
        self.dish_week_service = DishWeekService(self.queryset)
        self.dish_create_service = DishCreateService()

    def get_permissions(self):
        """ Права доступа """

        if self.action == 'list' or self.action == 'retrieve':
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = []
        return [permission() for permission in permission_classes]

    def list(self, request, *args, **kwargs):
        """ Получение списка меню """

        dish_list_service = self.dish_list_service.get_list_dishes()
        return dish_list_service

    def create(self, request, *args, **kwargs):
        """ Создание блюда """

        return self.dish_create_service.dish_create(request)

    @action(["get"], detail=False)
    def get_dish_week(self, request, *args, **kwargs):
        """ Получение блюд недели """

        dish_week_service = self.dish_week_service.get_dish_week()
        return dish_week_service
