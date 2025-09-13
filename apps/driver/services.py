from rest_framework.response import Response
from rest_framework import status

from .models import Transport, Driver, HistoryDriver
from ..student.models import Student
from ..user.models import User
from .serializers.driver import RouteSerializer 


class RouteCreateService:
    """ Сервис для создания маршрута """

    @staticmethod
    def route_create(request) -> Response:
        """ Создание маршрута """

        transport_id = request.data.get('transport')
        driver_id = request.data.get('driver')
        senior_id = request.data.get('senior')
        children_ids = request.data.get('children')

        try:
            transport = Transport.objects.get(id=transport_id)
        except Transport.DoesNotExist:
            return Response({'detail': 'Транспорт не найден'}, status=status.HTTP_403_FORBIDDEN)

        try:
            driver = Driver.objects.get(id=driver_id)
        except Driver.DoesNotExist:
            return Response({'detail': 'Водитель не найден'}, status=status.HTTP_403_FORBIDDEN)

        try:
            senior = User.objects.get(id=senior_id)
        except User.DoesNotExist:
            return Response({'detail': 'Старший не найден'}, status=status.HTTP_403_FORBIDDEN)

        try:
            children = Student.objects.filter(id__in=children_ids)
        except Student.DoesNotExist:
            return Response({'detail': 'Дети не найдены'}, status=status.HTTP_403_FORBIDDEN)

        serializer = RouteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        route = serializer.save(transport=transport, driver=driver, senior=senior)
        route.children.set(children)

        HistoryDriver.objects.create(
            transport=transport,
            driver=driver
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)