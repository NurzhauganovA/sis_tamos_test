from rest_framework import viewsets

from apps.sms.models import SmsLog
from apps.sms.serializers import SmsLogSerializer


class SmsLogView(viewsets.ModelViewSet):
    queryset = SmsLog.objects.all()
    serializer_class = SmsLogSerializer
    http_method_names = ['get']
