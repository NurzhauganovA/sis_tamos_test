from rest_framework import serializers

from apps.sms.models import SmsLog


class SmsLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmsLog
        fields = '__all__'
