from rest_framework import serializers
from django.utils import timezone

from .models import (
    Application,
    ApplicationType,
    ServiceProvider,
    ApplicationFile,
    ApplicationComment,
    ApplicationStatusHistory
)
from apps.student.models import Student
from apps.user.serializers import UserSerializer
from ..contract.models import StudentMS


def get_student_data_by_id(student_id):
    try:
        student_ms = StudentMS.objects.using('ms_sql').get(id=student_id)
        return {
            'id': student_ms.id,
            'full_name': student_ms.full_name,
            'iin': student_ms.iin,
        }
    except StudentMS.DoesNotExist:
        return None


class ServiceProviderSerializer(serializers.ModelSerializer):
    account = UserSerializer(read_only=True)

    class Meta:
        model = ServiceProvider
        fields = [
            'id', 'name', 'bin_or_iin', 'service_type', 'description',
            'responsible_full_name', 'responsible_phone', 'responsible_email',
            'campus', 'subdivision1', 'subdivision2', 'account', 'is_active'
        ]


class ServiceProviderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProvider
        fields = [
            'id', 'name', 'bin_or_iin', 'service_type', 'description',
            'responsible_full_name', 'responsible_phone', 'responsible_email',
            'campus', 'subdivision1', 'subdivision2', 'account'
        ]


class ServiceProviderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProvider
        fields = [
            'name', 'bin_or_iin', 'service_type', 'description',
            'responsible_full_name', 'responsible_phone', 'responsible_email',
            'campus', 'subdivision1', 'subdivision2', 'account', 'is_active'
        ]


class AccountServiceProviderSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    fio = serializers.CharField()
    login = serializers.CharField()
    role = serializers.CharField()
    is_active = serializers.BooleanField()


class AccountCreateServiceProviderSerializer(serializers.Serializer):
    responsible_full_name = serializers.CharField()
    service_type = serializers.CharField()
    login = serializers.CharField()
    password = serializers.CharField()
    password2 = serializers.CharField()


class ApplicationCampusSerializer(serializers.Serializer):
    campuses = serializers.ListField(child=serializers.CharField())


class ApplicationTypeSerializer(serializers.ModelSerializer):
    service_provider = ServiceProviderSerializer(read_only=True)

    class Meta:
        model = ApplicationType
        fields = ['id', 'name', 'description', 'service_provider', 'is_active']


class ApplicationTypeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationType
        fields = ['name', 'description', 'service_provider']


class ApplicationTypeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationType
        fields = ['name', 'description', 'service_provider', 'is_active']


class ApplicationFileSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)

    class Meta:
        model = ApplicationFile
        fields = [
            'id', 'file', 'original_name',
            'uploaded_at', 'uploaded_by'
        ]


class ApplicationCommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = ApplicationComment
        fields = [
            'id', 'comment', 'is_internal',
            'created_at', 'author'
        ]


class ApplicationStatusHistorySerializer(serializers.ModelSerializer):
    changed_by = UserSerializer(read_only=True)

    class Meta:
        model = ApplicationStatusHistory
        fields = [
            'id', 'old_status', 'new_status', 'reason',
            'changed_at', 'changed_by'
        ]


class StudentSimpleSerializer(serializers.Serializer):
    """Простой сериализатор для данных студента из MS базы"""
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    iin = serializers.CharField(required=False, allow_null=True)


class ApplicationListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка заявок"""
    student_id = serializers.SerializerMethodField()
    application_type = ApplicationTypeSerializer(read_only=True)
    applicant = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    def get_student_id(self, obj):
        return get_student_data_by_id(obj.student_id)

    class Meta:
        model = Application
        fields = [
            'id', 'subject', 'campus', 'subdivision1', 'subdivision2', 'status',
            'status_display', 'student_id', 'student_class_num', 'student_class_liter',
            'application_type', 'applicant', 'assigned_to', 'created_at', 'updated_at'
        ]


class ApplicationDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор для заявки"""
    student = serializers.SerializerMethodField()
    application_type = ApplicationTypeSerializer(read_only=True)
    applicant = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    files = ApplicationFileSerializer(many=True, read_only=True)
    comments = ApplicationCommentSerializer(many=True, read_only=True)
    status_history = ApplicationStatusHistorySerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    def get_student(self, obj):
        return get_student_data_by_id(obj.student_id)

    class Meta:
        model = Application
        fields = [
            'id', 'subject', 'campus', 'subdivision1', 'subdivision2',
            'description', 'status', 'status_display', 'student',
            'student_class_num', 'student_class_liter', 'application_type',
            'applicant', 'assigned_to', 'rejection_reason', 'created_at', 'updated_at',
            'processed_at', 'completed_at', 'files', 'comments', 'status_history'
        ]


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания заявки"""
    uploaded_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        allow_empty=True
    )

    class Meta:
        model = Application
        fields = [
            'campus', 'subdivision1', 'subdivision2', 'application_type',
            'student_id', 'student_class_num', 'student_class_liter',
            'subject', 'description', 'uploaded_files'
        ]

    def validate_student_id(self, value):
        """Проверяем, что студент принадлежит текущему пользователю"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            login_format = str(request.user.login).split('+7')[1] if request.user.login.startswith(
                '+7') else request.user.login

            try:
                from apps.user.models import ParentMS
                parent_ms = ParentMS.objects.using('ms_sql').filter(phone=login_format).first()
                if not parent_ms:
                    raise serializers.ValidationError(
                        "Родительская учетная запись не найдена."
                    )

                student_exists = StudentMS.objects.using('ms_sql').filter(
                    id=value,
                    parent_id=parent_ms.id
                ).exists()

                if not student_exists:
                    raise serializers.ValidationError(
                        "Вы можете создавать заявки только для своих детей."
                    )
            except Exception as e:
                raise serializers.ValidationError(
                    f"Ошибка при проверке студента: {str(e)}"
                )
        return value

    def create(self, validated_data):
        uploaded_files = validated_data.pop('uploaded_files', [])
        request = self.context.get('request')

        validated_data['applicant'] = request.user

        application = super().create(validated_data)

        for file in uploaded_files:
            ApplicationFile.objects.create(
                application=application,
                file=file,
                original_name=file.name,
                uploaded_by=request.user
            )

        return application


class ApplicationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['campus', 'subdivision1', 'subdivision2', 'subject', 'description']


class ApplicationStatusUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления статуса заявки"""
    reason = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Application
        fields = ['status', 'reason']

    def validate(self, data):
        if data.get('status') == 'rejected' and not data.get('reason'):
            raise serializers.ValidationError({
                'reason': 'Причина отклонения обязательна при отклонении заявки.'
            })
        return data

    def update(self, instance, validated_data):
        old_status = instance.status
        new_status = validated_data.get('status', instance.status)
        reason = validated_data.pop('reason', '')

        # Обновляем заявку
        if new_status == 'rejected':
            instance.rejection_reason = reason
        elif new_status == 'in_progress':
            instance.processed_at = timezone.now()
            instance.assigned_to = self.context['request'].user
        elif new_status == 'completed':
            instance.completed_at = timezone.now()

        instance = super().update(instance, validated_data)

        # Сохраняем историю изменений
        if old_status != new_status:
            ApplicationStatusHistory.objects.create(
                application=instance,
                old_status=old_status,
                new_status=new_status,
                reason=reason,
                changed_by=self.context['request'].user
            )

        return instance


class ApplicationCommentCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания комментария"""

    class Meta:
        model = ApplicationComment
        fields = ['comment', 'is_internal']

    def create(self, validated_data):
        request = self.context.get('request')
        application = self.context.get('application')

        validated_data['author'] = request.user
        validated_data['application'] = application

        return super().create(validated_data)