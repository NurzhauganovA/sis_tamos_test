from django.db import models


class DishWeightName(models.Model):
    """ Модель для веса блюда """

    weight_name = models.CharField(max_length=50, null=False)  # ['грамм', 'штук', 'мл', 'ст']

    def __str__(self):
        return f'{self.weight_name}'

    class Meta:
        verbose_name = 'Dish weight name'
        verbose_name_plural = 'Dish weight names'
        db_table = 'dish_weight_name'


class DishWeek(models.Model):
    """ Модель для блюд недели """

    dish_date = models.DateField(null=False)
    dish_name = models.CharField(max_length=255, null=False)  # soup
    dish_weight = models.PositiveSmallIntegerField(null=False)  # 250
    dish_weight_id = models.ForeignKey(DishWeightName, on_delete=models.SET_NULL, null=True)  # 1
    eating = models.CharField(max_length=255, null=False)

    def __str__(self):
        return f'{self.dish_date} - {self.dish_name} - {self.eating}'

    class Meta:
        verbose_name = 'Dish week'
        verbose_name_plural = 'Dish weeks'
        db_table = 'dish_week'
