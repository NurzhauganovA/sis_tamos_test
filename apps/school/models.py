from django.db import models
from django.utils.translation import gettext_lazy as _


class School(models.Model):
    """ Модель школы """

    sSchool_logo = models.ImageField(upload_to='school/logo/', null=True)
    sSchool_name = models.CharField(max_length=155, null=False)
    sSchool_address = models.CharField(max_length=155, null=False)
    sSchool_direct = models.CharField(max_length=155, null=False)
    sSchool_language = models.CharField(max_length=155, null=False)
    isSchool = models.PositiveSmallIntegerField(null=False)
    sCommentary = models.CharField(max_length=255, null=True)
    sBin = models.CharField(max_length=12, null=False)

    def __str__(self):
        return self.sSchool_name

    class Meta:
        verbose_name = _("School")
        verbose_name_plural = _("Schools")
        db_table = 'school'


class SchoolRequisites(models.Model):
    """ Модель реквизитов школы """

    school = models.OneToOneField(School, on_delete=models.CASCADE, null=False)
    bank_name = models.CharField(max_length=155, null=False)
    bank_address = models.CharField(max_length=155, null=False)
    bank_bik = models.CharField(max_length=9, null=False)
    bank_iik = models.CharField(max_length=20, null=False)
    bank_kbe = models.CharField(max_length=20, null=False)
    bank_rs = models.CharField(max_length=20, null=False)
    bank_ks = models.CharField(max_length=20, null=False)
    bank_bin = models.CharField(max_length=12, null=False)

    def __str__(self):
        return f'{self.school} - {self.bank_name}'

    class Meta:
        verbose_name = _("SchoolRequisite")
        verbose_name_plural = _("SchoolRequisites")
        db_table = 'schoolRequisites'


class SchoolMS(models.Model):
    """ Модель школы, который хранится в MS SQL """

    sSchool_name = models.CharField(max_length=155, null=False)
    sSchool_address = models.CharField(max_length=155, null=False)
    sSchool_direct = models.CharField(max_length=155, null=False)
    sSchool_language = models.CharField(max_length=155, null=False)
    isSchool = models.PositiveSmallIntegerField(null=False)
    sCommentary = models.CharField(max_length=255, null=True)
    sBin = models.CharField(max_length=12, null=False)

    def __str__(self):
        return self.sSchool_name

    class Meta:
        verbose_name = _("SchoolMs")
        verbose_name_plural = _("SchoolsMs")
        db_table = 'spr_School'
        managed = False


class Class(models.Model):
    """ Модель класса """

    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True)
    class_num = models.IntegerField(null=False)
    class_liter = models.CharField(max_length=1, null=False)
    commentary = models.CharField(max_length=255, null=True)
    isActive = models.BooleanField(default=True)
    teacher = models.ForeignKey('user.User', on_delete=models.SET_NULL, null=True, related_name='classroom_teacher')
    isGraduated = models.BooleanField(default=False)
    max_class_num = models.PositiveIntegerField(default=11)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.class_num}{self.class_liter}'

    class Meta:
        verbose_name = 'Class'
        verbose_name_plural = 'Classes'
        db_table = 'class'
