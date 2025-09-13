from rest_framework import serializers
from ..models import DishWeightName, DishWeek


class DishWeightNameSerializer(serializers.ModelSerializer):
    """ Сериализатор для веса блюда """

    class Meta:
        model = DishWeightName
        fields = '__all__'


class DishWeekSerializer(serializers.ModelSerializer):
    """ Сериализатор для блюда недели """

    class Meta:
        model = DishWeek
        fields = ['id', 'dish_date', 'dish_name', 'dish_weight', 'dish_weight_id', 'eating']
