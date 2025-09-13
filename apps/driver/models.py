from django.db import models

from apps.student.models import Student
from apps.user.models import User


class Driver(models.Model):
    """ Водитель """

    full_name = models.CharField(max_length=150, verbose_name='ФИО водителя')
    phone = models.CharField(max_length=150, verbose_name='Телефон водителя')

    def __str__(self):
        return f'{self.full_name}'


class Transport(models.Model):
    """ Транспорт """

    transport_model = models.CharField(max_length=150, verbose_name='Модель транспорта')
    transport_number = models.CharField(max_length=150, verbose_name='Номер транспорта')
    number_of_seats = models.IntegerField(verbose_name='Количество мест')

    def __str__(self):
        return f'{self.transport_model} {self.transport_number}'

    class Meta:
        verbose_name = 'Transport'
        verbose_name_plural = 'Transports'


class Route(models.Model):
    """ Маршрут """

    name = models.CharField(max_length=150, verbose_name='Название маршрута')
    transport = models.ForeignKey(Transport, on_delete=models.SET_NULL, null=True, verbose_name='Транспорт')
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, verbose_name='Водитель')
    senior = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Старший')
    children = models.ManyToManyField(Student, related_name='children', verbose_name='Дети')
    is_active = models.BooleanField(default=True, verbose_name='Активный')

    def __str__(self):
        return f'Route: {self.name} <---> Senior: {self.senior}'

    class Meta:
        verbose_name = 'Route'
        verbose_name_plural = 'Routes'


class HistoryDriver(models.Model):
    """ История водителей маршрута если водитель меняется """

    transport = models.ForeignKey(Transport, on_delete=models.CASCADE, verbose_name='Маршрут')
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, verbose_name='Водитель')
    date = models.DateTimeField(auto_now_add=True, verbose_name='Дата')

    def __str__(self):
        return f'{self.transport} {self.driver}'

    class Meta:
        verbose_name = 'HistoryDriver'
        verbose_name_plural = 'HistoryDrivers'
