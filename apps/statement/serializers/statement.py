from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.statement.models import StatementDocFile, Statement


class StatementDocFileSerializer(serializers.ModelSerializer):
    """ Сериализатор для файлов заявления """
    class Meta:
        model = StatementDocFile
        fields = ['file']
        kwargs = {
            'file': {
                'write_only': True,
                'required': False,
                'allow_null': True,
                'allow_empty_file': True,
            }
        }


class StatementSerializer(serializers.ModelSerializer):
    """
        Сериализатор для заявления.
        Поля uploaded_files и statement_files используются для загрузки файлов.
        uploaded_files - для загрузки файлов с фронта.
        statement_files - для отображения файлов в заявлении.
    """

    statement_files = StatementDocFileSerializer(many=True, read_only=True)
    uploaded_files = serializers.ListField(
        child=serializers.FileField(max_length=100000, allow_empty_file=True, use_url=False, allow_null=True),
        write_only=True,
        required=False
    )

    class Meta:
        model = Statement
        fields = ['id', 'full_name', 'iin', 'parent',
                  'birthday', 'num_of_doc', 'is_nutrition', 'is_transport', 'student_class',
                  'student_position', 'commentary', 'student_image', 'statement_files', 'uploaded_files']

    def create(self, validated_data):
        """
            Переопределение метода create для сохранения файлов.
            При сохранении файлов используется транзакция.
        """

        if 'uploaded_files' not in validated_data:
            return Statement.objects.create(**validated_data)

        uploaded_files = validated_data.pop('uploaded_files', None)
        statement = Statement.objects.create(**validated_data)

        statement_files = [
            StatementDocFile(statement=statement, file=file) for file in uploaded_files
        ]

        for file in statement_files:
            file.full_clean()

        try:
            with transaction.atomic():
                StatementDocFile.objects.bulk_create(statement_files)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        return statement
