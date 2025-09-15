# apps/contract/urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    Contract,
    ContractFood,
    ContractDriver,
    SignContractWithEDS,
    ContractDownload,
    RawContractTemplateView,
    MarkedUpContractTemplateView,
    ContractListReportView, SignatureVerificationView
)
from .views import (
    ContractSigningView,
    ContractSignaturesView,
    SignatureValidityView,
    ContractSigningDataView,
    ContractSigningWebView
)

router = DefaultRouter()
router.register("study", Contract, basename="study")
router.register("food", ContractFood, basename="food")
router.register("driver", ContractDriver, basename="driver")
router.register("download", ContractDownload, basename="download")
router.register("sign", SignContractWithEDS, basename="sign")
router.register("raw-template", RawContractTemplateView, basename="raw contract template")
router.register("markedup-template", MarkedUpContractTemplateView, basename="marked up contract template")
router.register("report", ContractListReportView, basename="report")

contract_signature_patterns = [
    # Подписание контракта
    path('contracts/sign/', ContractSigningView.as_view(), name='contract-sign'),

    path('contracts/<str:contract_num>/signatures/', ContractSignaturesView.as_view(), name='contract-signatures'),

    # Проверка валидности подписи
    path('signatures/<str:signature_uid>/validity/', SignatureValidityView.as_view(), name='signature-validity'),

    # Получение данных для подписания
    path('contracts/<str:contract_num>/signing-data/', ContractSigningDataView.as_view(), name='contract-signing-data'),

    # Веб-интерфейс для тестирования подписания
    path('contracts/<str:contract_num>/sign-web/', ContractSigningWebView.as_view(), name='contract-sign-web'),

    path('signature-verification/<str:signature_uid>/', SignatureVerificationView.as_view(), name='signature-verification'),
]

urlpatterns = router.urls
urlpatterns += contract_signature_patterns