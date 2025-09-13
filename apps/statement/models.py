from django.core.validators import FileExtensionValidator
from django.db import models
from rest_framework.exceptions import ValidationError

from apps.user.models import User


class Statement(models.Model):
    """ Модель заявления для поступления в школу """

    parent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='parent')
    full_name = models.CharField(max_length=255, null=False)
    iin = models.CharField(max_length=12, null=False)
    birthday = models.DateField(null=False)
    num_of_doc = models.CharField(max_length=50, null=False)
    is_nutrition = models.BooleanField(default=False)
    is_transport = models.BooleanField(default=False)
    student_class = models.CharField(max_length=255, null=True)
    student_position = models.CharField(max_length=255, null=True)
    commentary = models.CharField(max_length=255, null=True)
    student_image = models.ImageField(upload_to='statement/stud_images/', null=True)

    def __str__(self):
        return f'{self.full_name}'

    class Meta:
        verbose_name = 'Statement'
        verbose_name_plural = 'Statements'
        db_table = 'statement'


class StatementDocFile(models.Model):
    """ Модель документов для заявления """

    statement = models.ForeignKey(Statement,
                                  on_delete=models.CASCADE,
                                  null=True,
                                  blank=True,
                                  related_name='statement_files'
                                  )
    file = models.FileField(
        upload_to='statement/doc_files/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])]
    )

    def clean(self):
        """ Проверка на валидность расширения файла """

        super().clean()
        if self.file:
            extension = self.file.name.split('.')[-1]
            if extension.lower() not in ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']:
                raise ValidationError('Invalid file extension. Allowed extensions are: pdf, doc, docx, jpg, jpeg, png.')

    def save(self, *args, **kwargs):
        """ Переопределение метода save для валидации """

        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Statement doc file'
        verbose_name_plural = 'Statement doc files'
        db_table = 'statement_doc_file'
