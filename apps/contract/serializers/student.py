from rest_framework.serializers import ModelSerializer

from ..models import ParentMS, StudentMS


class ParentMSSerializer(ModelSerializer):
    """ Сериализатор для получения данных о родителе """

    class Meta:
        model = ParentMS
        fields = ['id', 'full_name', 'iin', 'num_of_doc', 'issued_by', 'phone', 'email']


class StudentMSSerializer(ModelSerializer):
    """ Сериализатор для получения данных о студенте """

    parent_id = ParentMSSerializer(read_only=True)

    class Meta:
        model = StudentMS
        fields = ['id', 'full_name', 'iin', 'phone', 'birthday', 'email', 'parent_id']
