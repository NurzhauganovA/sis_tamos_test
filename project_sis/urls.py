from django.conf.urls.static import static
from django.conf import settings
from django.urls import path, include, re_path
from django.contrib import admin
from django.contrib.auth import views as auth_views

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.user.views import CustomTokenObtainPairView

api_version = 'api/v1/'

urlpatterns = [
    path(f'{api_version}swagger/', SpectacularAPIView.as_view(), name='schema'),
    # SWAGGER UI:
    path(f'{api_version}swagger/ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path(f'{api_version}schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    path('admin/', admin.site.urls),

    path(f'{api_version}api-auth/', include('rest_framework.urls')),

    path(f'{api_version}', include([re_path(r"^jwt/create/?", CustomTokenObtainPairView.as_view(), name="jwt-create")])),

    path(f'{api_version}', include('apps.user.urls')),
    path(f'{api_version}school/', include('apps.school.urls')),
    path(f'{api_version}dish/', include('apps.dish.urls')),
    path(f'{api_version}statement/', include('apps.statement.urls')),
    path(f'{api_version}student/', include('apps.student.urls')),
    path(f'{api_version}', include('apps.sms.urls')),
    path(f'{api_version}contract/', include('apps.contract.urls')),
    path(f'{api_version}driver/', include('apps.driver.urls')),
    path(f'{api_version}payment/', include('apps.payment.urls')),

    path(f'{api_version}token/logout/', auth_views.LogoutView.as_view(), name='logout'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
