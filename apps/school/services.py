from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response

from .models import School, Class
from .serializers.stud_class import CreateClassSerializer
from ..user.models import User


class ClassCreateService:
    """ Сервис для создания нового класса """

    @staticmethod
    def class_create(request, pk) -> Response:
        school = School.objects.filter(id=pk).first()
        if not school:
            return Response({'message': 'Школа не найдена!'}, status=status.HTTP_403_FORBIDDEN)

        teacher = request.data.get('teacher', None)

        if teacher is not None:
            teacher_user = User.objects.filter(id=teacher).first()
            if teacher_user is None:
                return Response({'message': 'Указанный учитель не найден!'}, status=status.HTTP_403_FORBIDDEN)
            if teacher_user.role.role_name != 'Учитель':
                return Response({'message': 'Указанный пользователь не является учителем!'},
                                status=status.HTTP_403_FORBIDDEN)

        request.data['school'] = pk

        try:
            new_class = CreateClassSerializer(data=request.data, partial=True)
            new_class.is_valid(raise_exception=True)
            new_class.save()
        except IntegrityError:
            last_class = Class.objects.last()
            new_class_id = last_class.id + 1
            request.data['id'] = new_class_id
            new_class = CreateClassSerializer(data=request.data, partial=True)
            new_class.is_valid(raise_exception=True)
            new_class.save()

        return Response(new_class.data, status=status.HTTP_201_CREATED)
