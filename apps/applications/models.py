from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.user.models import User


class ServiceProvider(models.Model):
    """Юридическое лицо, предоставляющее услуги"""
    name = models.CharField(max_length=200, verbose_name=_("Наименование"))
    bin_or_iin = models.CharField(max_length=20, verbose_name=_("БИН/ИИН"))
    service_type = models.CharField(max_length=100, verbose_name=_("Тип услуги"), null=True, blank=True)
    description = models.TextField(blank=True, verbose_name=_("Описание"), null=True)

    responsible_full_name = models.CharField(max_length=200, verbose_name=_("Ответственный за заявки"))
    responsible_phone = models.CharField(max_length=20, verbose_name=_("Телефон ответственного"))
    responsible_email = models.EmailField(max_length=200, verbose_name=_("Email ответственного"), null=True, blank=True)

    campus = models.CharField(max_length=100, verbose_name=_("Кампус"), null=True, blank=True)
    subdivision1 = models.CharField(max_length=100, verbose_name=_("Подразделение 1"), null=True, blank=True)
    subdivision2 = models.CharField(max_length=100, verbose_name=_("Подразделение 2"), null=True, blank=True)

    is_active = models.BooleanField(default=True, verbose_name=_("Активен"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Поставщик услуг")
        verbose_name_plural = _("Поставщики услуг")
        db_table = 'service_provider'

    def __str__(self):
        return f"{self.name} - {self.service_type}"

    def clean(self):
        # check unique constraint for bin_or_iin
        if ServiceProvider.objects.exclude(id=self.id).filter(bin_or_iin=self.bin_or_iin).exists():
            raise ValidationError({'bin_or_iin': _("БИН/ИИН должен быть уникальным.")})


class ApplicationType(models.Model):
    """Типы заявок"""
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Название типа"))
    description = models.TextField(blank=True, verbose_name=_("Описание"))
    service_provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name='application_types',
        verbose_name=_("Поставщик услуг")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Активен"))

    class Meta:
        verbose_name = _("Тип заявки")
        verbose_name_plural = _("Типы заявок")
        db_table = 'application_type'

    def __str__(self):
        return self.name


class Application(models.Model):
    """Основная модель заявки"""

    STATUS_CHOICES = [
        ('new', _('Новая')),
        ('in_progress', _('В работе')),
        ('completed', _('Завершена')),
        ('rejected', _('Отклонена')),
    ]

    campus = models.CharField(max_length=100, verbose_name=_("Кампус"), null=True, blank=True)
    subdivision1 = models.CharField(max_length=100, verbose_name=_("Подразделение 1"), null=True, blank=True)
    subdivision2 = models.CharField(max_length=100, verbose_name=_("Подразделение 2"), null=True, blank=True)

    # Основная информация
    applicant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name=_("Заявитель")
    )
    student_id = models.IntegerField(verbose_name=_("Ученик (ID из MS)"))
    student_class_num = models.CharField(max_length=10, verbose_name=_("Класс"))
    student_class_liter = models.CharField(max_length=10, verbose_name=_("Литер"), blank=True, null=True)

    application_type = models.ForeignKey(
        ApplicationType,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name=_("Тип заявки")
    )

    # Детали заявки
    subject = models.CharField(max_length=200, verbose_name=_("Тема заявки"))
    description = models.TextField(verbose_name=_("Описание"))

    # Статус и обработка
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name=_("Статус")
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_applications',
        verbose_name=_("Назначено")
    )

    # Причина отклонения
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Причина отклонения")
    )

    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Дата обработки"))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Дата завершения"))

    class Meta:
        verbose_name = _("Заявка")
        verbose_name_plural = _("Заявки")
        db_table = 'application'
        ordering = ['-created_at']

    def __str__(self):
        return f"Заявка #{self.id} - {self.subject}"


class ApplicationFile(models.Model):
    """Прикрепленные файлы к заявке"""
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name=_("Заявка")
    )
    file = models.FileField(
        upload_to='applications/files/',
        verbose_name=_("Файл")
    )
    original_name = models.CharField(max_length=255, verbose_name=_("Оригинальное имя файла"))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата загрузки"))
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("Загружено пользователем")
    )

    class Meta:
        verbose_name = _("Файл заявки")
        verbose_name_plural = _("Файлы заявок")
        db_table = 'application_file'

    def __str__(self):
        return f"Файл для заявки #{self.application.id}"


class ApplicationComment(models.Model):
    """Комментарии к заявке"""
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_("Заявка")
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("Автор")
    )
    comment = models.TextField(verbose_name=_("Комментарий"))
    is_internal = models.BooleanField(
        default=False,
        verbose_name=_("Внутренний комментарий")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))

    class Meta:
        verbose_name = _("Комментарий к заявке")
        verbose_name_plural = _("Комментарии к заявкам")
        db_table = 'application_comment'
        ordering = ['created_at']

    def __str__(self):
        return f"Комментарий к заявке #{self.application.id}"


class ApplicationStatusHistory(models.Model):
    """История изменений статуса заявки"""
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name=_("Заявка")
    )
    old_status = models.CharField(max_length=20, verbose_name=_("Предыдущий статус"))
    new_status = models.CharField(max_length=20, verbose_name=_("Новый статус"))
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("Изменено пользователем")
    )
    reason = models.TextField(blank=True, verbose_name=_("Причина изменения"))
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата изменения"))

    class Meta:
        verbose_name = _("История статуса заявки")
        verbose_name_plural = _("История статусов заявок")
        db_table = 'application_status_history'
        ordering = ['changed_at']

    def __str__(self):
        return f"Заявка #{self.application.id}: {self.old_status} → {self.new_status}"