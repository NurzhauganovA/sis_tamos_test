from collections import defaultdict
from datetime import date, timedelta

from rest_framework import status
from rest_framework.response import Response

from .models import DishWeightName
from .serializers.dish_week import DishWeightNameSerializer, DishWeekSerializer


class DishListService:
    """ Сервис для работы с блюдами """

    def __init__(self, queryset) -> None:
        self.queryset = queryset

    def get_list_dishes(self) -> Response:
        queryset = self.queryset.order_by('dish_date')
        data = defaultdict(lambda: defaultdict(list))

        for dish_week in queryset:
            day_of_week = dish_week.dish_date.strftime('%d.%m.%Y')
            data[day_of_week][dish_week.eating].append({
                'id': dish_week.id,
                'dish_name': dish_week.dish_name,
                'dish_weight': dish_week.dish_weight,
                'dish_weight_id': DishWeightNameSerializer(dish_week.dish_weight_id).data.get('weight_name')
            })

        return Response(data)


class DishWeekService:
    """
        Сервис для работы с блюдами на неделю.
        Если в базе данных нет блюд на текущую неделю, то этот день не отображается.
    """

    def __init__(self, queryset) -> None:
        self.queryset = queryset

    @staticmethod
    def get_weekday_order(weekday) -> int:
        order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        return order.index(weekday)

    def get_dish_week(self) -> Response:
        queryset = self.queryset

        start_of_week = date.today() - timedelta(days=date.today().weekday())
        end_of_week = start_of_week + timedelta(days=4)

        data = defaultdict(lambda: defaultdict(list))

        for dish_week in queryset.filter(dish_date__range=[start_of_week, end_of_week]):
            day_of_week = dish_week.dish_date.strftime('%A')

            if day_of_week not in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
                continue

            meal_name = dish_week.eating

            data[day_of_week][meal_name].append({
                'id': dish_week.id,
                'dish_name': dish_week.dish_name,
                'dish_weight': dish_week.dish_weight,
                'dish_weight_id': DishWeightNameSerializer(dish_week.dish_weight_id).data.get('weight_name')
            })

        sorted_data = sorted(data.items(), key=lambda x: self.get_weekday_order(x[0]))
        sorted_data_list = [{'day': day_name, 'meals': meals} for day_name, meals in sorted_data]

        return Response(sorted_data_list)


class DishCreateService:
    """ Сервис для создания блюд """

    @staticmethod
    def dish_create(request) -> Response:
        dish_weight = request.data.get('dish_weight_id')

        try:
            DishWeightName.objects.get(id=dish_weight).id
        except DishWeightName.DoesNotExist:
            return Response({'error': 'Weight does not exist'}, status=status.HTTP_400_BAD_REQUEST)

        dish_week_serializer = DishWeekSerializer(data=request.data)
        dish_week_serializer.is_valid(raise_exception=True)
        dish_week_serializer.save()
        return Response(dish_week_serializer.data, status=status.HTTP_201_CREATED)
