from rest_framework import status, pagination, filters
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Route, Transport, Driver, HistoryDriver
from .serializers.driver import RouteSerializer, TransportSerializer, DriverSerializer, HistoryDriverSerializer
from ..student.models import Student
from ..user.models import User
from .services import RouteCreateService


class RouteViewSet(ModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    http_method_names = ['get', 'post', 'put']
    create_service = RouteCreateService()

    def create(self, request, *args, **kwargs):
        """ Создание маршрута """

        new_route = self.create_service.route_create(request)
        return new_route


class TransportViewSet(ModelViewSet):
    queryset = Transport.objects.all()
    serializer_class = TransportSerializer
    http_method_names = ['get', 'post', 'put']


class DriverViewSet(ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    http_method_names = ['get', 'post', 'put']


class HistoryDriverViewSet(ModelViewSet):
    queryset = HistoryDriver.objects.all()
    serializer_class = HistoryDriverSerializer
    http_method_names = ['get', 'post', 'put']
