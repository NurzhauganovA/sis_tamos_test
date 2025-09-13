from rest_framework import status
from rest_framework.response import Response

from .models import Student
from ..school.models import Class
from .permissions import IsParentRole
from .serializers.student import CreateStudentSerializer, StudentSerializer
from ..user.permissions import IsAdmin


class StudentCreateService:
    def student_create(self, request) -> Response:
        if IsParentRole().has_permission(request, self):
            request.data['parent'] = request.user.id

            try:
                class_id = Class.objects.get(id=request.data['stud_class']).id
                request.data['stud_class'] = class_id
            except Class.DoesNotExist:
                return Response({'error': 'Class does not exist'}, status=status.HTTP_400_BAD_REQUEST)

            additional_parent = request.data.get('additional_parent')
            if additional_parent == request.user.id:
                return Response({'error': 'You cannot add yourself as additional parent'}, status=status.HTTP_400_BAD_REQUEST)

            new_student = CreateStudentSerializer(data=request.data)
            new_student.is_valid(raise_exception=True)
            new_student.save()

            return Response(new_student.data, status=status.HTTP_201_CREATED)
        return Response({'error': 'You are no parent user!'}, status=status.HTTP_403_FORBIDDEN)


class StudentUpdateService:
    def student_update(self, request, pk) -> Response:
        instance = Student.objects.get(id=pk)
        if IsParentRole().has_permission(request, self) or IsAdmin().has_permission(request, self):
            student = StudentSerializer(instance, data=request.data, partial=True)
            student.is_valid(raise_exception=True)
            student.save()

            return Response(student.data)
        return Response({'error': 'You are no parent or admin user!'}, status=status.HTTP_403_FORBIDDEN)
