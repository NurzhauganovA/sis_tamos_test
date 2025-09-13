from rest_framework.routers import DefaultRouter
from apps.sms.views import SmsLogView


router = DefaultRouter()
router.register("sms_log", SmsLogView, basename="sms_log")

urlpatterns = router.urls
