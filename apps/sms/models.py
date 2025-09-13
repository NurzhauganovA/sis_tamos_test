from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from apps.user.models import User


class SmsLog(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    sms_id = models.IntegerField(null=False)
    recipient = PhoneNumberField(null=True)
    text = models.CharField(max_length=250, null=False)

    def __str__(self):
        return self.recipient

    class Meta:
        verbose_name = _("SmsLog")
        verbose_name_plural = _("SmsLogs")
        db_table = 'sms_log'
