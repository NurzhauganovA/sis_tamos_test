from django.contrib.auth.models import UserManager
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
from phonenumber_field.modelfields import PhoneNumberField
from rest_framework.exceptions import ValidationError

from apps.school.models import School


class CustomUserManager(UserManager):
    def create_user(self, login, password=None, is_active=False, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', is_active)

        user = self.model(login=login, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, login, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        extra_fields.setdefault('role', None)
        extra_fields.setdefault('is_work', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(login, password, **extra_fields)


class UserRole(models.Model):
    role_name = models.CharField(
        max_length=150,
        unique=True,
        error_messages={
            'unique': _("This user role already exists."),
        },
    )

    def __str__(self):
        return self.role_name

    class Meta:
        verbose_name = _("User Role")
        verbose_name_plural = _("User Roles")
        db_table = 'user_role'


class UserRoleMS(models.Model):
    role_name = models.CharField(
        max_length=150,
        unique=True,
        error_messages={
            'unique': _("This user role already exists."),
        },
    )

    def __str__(self):
        return self.role_name

    class Meta:
        verbose_name = _("User Role")
        verbose_name_plural = _("User Roles")
        db_table = 'spr_Role'
        managed = False


class User(AbstractUser):
    school = models.ManyToManyField(School, related_name='school_employees', null=True)
    role = models.ForeignKey(UserRole, null=True, on_delete=models.SET_NULL)
    login = models.CharField(
        _('login'),
        max_length=150,
        unique=True,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        error_messages={
            'unique': _("A user with that login already exists.")
        },
    )
    fio = models.CharField(max_length=100, null=False)
    is_work = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    reason_for_deletion = models.CharField(max_length=100, null=True)

    username = None
    first_name = None
    last_name = None
    email = None
    groups = None
    user_permissions = None

    objects = CustomUserManager()

    USERNAME_FIELD = 'login'
    REQUIRED_FIELDS = ['fio', 'password']

    def __str__(self):
        return self.login

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        db_table = 'user'


class UserInfo(models.Model):
    user = models.OneToOneField(User, null=False, on_delete=models.CASCADE, related_name='user_info')
    photo_avatar = models.ImageField(upload_to='user/avatar/', null=True, blank=True)
    address = models.CharField(max_length=100, null=True)
    contacts = models.CharField(max_length=100, null=True)
    email = models.CharField(max_length=100, null=True)
    iin = models.CharField(max_length=100, null=True)
    num_of_doc = models.CharField(max_length=100, null=True)
    issued_by = models.CharField(max_length=100, null=True)
    issue_date = models.DateField(null=True, blank=True)
    work_place = models.CharField(max_length=100, null=True, blank=True)
    work_position = models.CharField(max_length=100, null=True, blank=True)
    is_teacher = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.user.fio

    class Meta:
        verbose_name = _("UserInfo")
        verbose_name_plural = _("UserInfo")
        db_table = 'user_info'


class UserDocFile(models.Model):
    user = models.ForeignKey(
        UserInfo,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='user_files'
    )
    file = models.FileField(
        upload_to='user/parent/doc_files/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])]
    )

    def clean(self):
        super().clean()
        if self.file:
            extension = self.file.name.split('.')[-1]
            if extension.lower() not in ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']:
                raise ValidationError(
                    'Invalid file extension. Allowed extensions are: pdf, doc, docx, jpg, jpeg, png.'
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'UserDocFile'
        verbose_name_plural = 'UserDocFiles'
        db_table = 'user_doc_file'


class UserMS(models.Model):
    role_id = models.SmallIntegerField(null=False)
    login = models.CharField(max_length=100, null=False)
    pass_c = models.CharField(max_length=100, null=False, db_column='pass')
    fio = models.CharField(max_length=100, null=False)
    iswork = models.BooleanField(default=False)
    password = models.CharField(max_length=250, null=False)
    code = models.CharField(max_length=250, null=False)

    def __str__(self):
        return self.login

    class Meta:
        verbose_name = _("UserMS")
        verbose_name_plural = _("UserMS")
        db_table = 'spr_Users'
        managed = False


class ParentMS(models.Model):
    full_name = models.CharField(max_length=100, null=False)
    address = models.CharField(max_length=100, null=False)
    contacts = models.CharField(max_length=100, null=False)
    email = models.CharField(max_length=100, null=False)
    iin = models.CharField(max_length=100, null=False)
    is_teacher = models.BooleanField(default=False)
    num_of_doc = models.CharField(max_length=100, null=False)
    issued_by = models.CharField(max_length=100, null=False)
    issue_date = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=100, null=False)
    work_place = models.CharField(max_length=100, null=False)
    work_position = models.CharField(max_length=100, null=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = _("ParentMS")
        verbose_name_plural = _("ParentMS")
        db_table = 't_Parents'
        managed = False


class AdditionalParent(models.Model):
    main_user = models.OneToOneField(User, on_delete=models.SET_NULL, related_name='additional_parent', null=True)
    photo_avatar = models.ImageField(upload_to='user/additional_parent/avatar/', null=True, blank=True)
    phone_number = PhoneNumberField(null=True, blank=True)
    email = models.EmailField(_('email address'), null=True, blank=True)
    full_name = models.CharField(max_length=100, null=True, blank=True)
    address = models.CharField(max_length=150, null=True, blank=True)
    iin = models.CharField(max_length=255, null=True, blank=True)
    num_of_doc = models.CharField(max_length=255, null=True, blank=True)
    is_teacher = models.BooleanField(default=False)
    issued_by = models.CharField(max_length=255, null=True, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    contacts = models.CharField(max_length=255, null=True, blank=True)
    work_place = models.CharField(max_length=255, null=True, blank=True)
    work_position = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = 'Additional parent'
        verbose_name_plural = 'Additional parents'
        db_table = 'additional_parent'


class AdditionalParentUserDocFile(models.Model):
    additional_parent_user = models.ForeignKey(
        AdditionalParent,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='additional_parent_user_files'
    )
    file = models.FileField(
        upload_to='user/additional_parent/doc_files/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])]
    )

    def clean(self):
        super().clean()
        if self.file:
            extension = self.file.name.split('.')[-1]
            if extension.lower() not in ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']:
                raise ValidationError('Invalid file extension. Allowed extensions are: pdf, doc, docx, jpg, jpeg, png.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'AdditionalParentUserDocFile'
        verbose_name_plural = 'AdditionalParentUserDocFiles'
        db_table = 'additional_parent_user_doc_file'
