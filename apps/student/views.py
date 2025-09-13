from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from .serializers.student import StudentSerializer
from ..contract.models import StudentMS
from ..user.models import ParentMS

from .services import StudentCreateService, StudentUpdateService


class StudentViewSet(ModelViewSet):
    serializer_class = StudentSerializer
    http_method_names = ['get', 'post', 'put']
    permission_classes = [IsAuthenticated]
    create_service = StudentCreateService()
    update_service = StudentUpdateService()

    def get_queryset(self):
        login_format = str(self.request.user.login).split('+7')[1]
        try:
            return StudentMS.objects.using('ms_sql').filter(parent_id=ParentMS.objects.using('ms_sql').filter(phone=login_format).first().id)
        except AttributeError:
            parent = ParentMS.objects.using('ms_sql').filter(phone=login_format).first()
            if parent:
                return StudentMS.objects.using('ms_sql').filter(parent_id=parent.id)
            else:
                return StudentMS.objects.using('ms_sql').none()

    def create(self, request, *args, **kwargs):
        return self.create_service.student_create(request)

    def update(self, request, *args, **kwargs):
        return self.update_service.student_update(request, kwargs['pk'])
