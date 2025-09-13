from rest_framework.viewsets import ModelViewSet

from .models import Statement
from .serializers.statement import StatementSerializer

from .services import StatementCreateService
from ..student.models import Student


class StatementViewSet(ModelViewSet):
    """ API endpoint для работы с заявлениями """

    queryset = Statement.objects.exclude(iin__in=Student.objects.values_list('iin', flat=True))
    serializer_class = StatementSerializer
    http_method_names = ['get', 'post', 'put']
    create_service = StatementCreateService()

    def create(self, request, *args, **kwargs):
        """ Создание заявления """

        new_statement = self.create_service.statement_create(request)
        return new_statement
