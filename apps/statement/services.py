from rest_framework import status
from rest_framework.response import Response

from .serializers.statement import StatementSerializer
from ..user.models import User


class StatementCreateService:
    """ Сервис для создания заявления на основе данных из запроса """

    @staticmethod
    def statement_create(request) -> Response:
        """ Создание заявления """

        try:
            request.data._mutable = True
        except AttributeError:
            return Response({'message': 'Invalid data'}, status=status.HTTP_403_FORBIDDEN)

        try:
            if request.data.get('parent') is not None:
                request.data['parent'] = User.objects.get(id=request.data['parent']).id
            else:
                request.data['parent'] = User.objects.get(id=request.user.id).id
        except User.DoesNotExist:
            return Response({'message': 'User does not exist'}, status=status.HTTP_403_FORBIDDEN)

        serializer = StatementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_statement = serializer.save()

        return Response(StatementSerializer(new_statement).data, status=status.HTTP_201_CREATED)
