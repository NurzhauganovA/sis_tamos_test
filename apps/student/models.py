from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

from apps.school.models import Class
from apps.user.models import User


class Student(models.Model):
    id_from_ms = models.IntegerField(null=True, blank=True, unique=True)
    photo_avatar = models.ImageField(upload_to='student/avatar/', null=True)
    birthday = models.DateField(null=True)
    full_name = models.CharField(max_length=150, null=True)
    iin = models.CharField(max_length=12, null=True, unique=True)
    leave = models.DateField(null=True)
    reason_leave = models.CharField(max_length=255, null=True)
    parent = models.ForeignKey(User, on_delete=models.CASCADE, null=False, related_name='main_parent')
    sex = models.SmallIntegerField(null=True)
    email = models.EmailField(null=True)
    phone = PhoneNumberField(null=True)
    stud_class = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, related_name='student_class')

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        db_table = 'student'
