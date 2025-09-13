from django.apps import AppConfig
from django_seed import Seed


class SchoolConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.school'

    # def ready(self):
    #     from .models import School, SchoolMS
    #
    #     seed = Seed()
    #     def fill_schools():
    #         schools_ms = SchoolMS.objects.using('ms_sql').all()
    #         schools = [
    #                 School(
    #                     sSchool_name=school_ms.sSchool_name,
    #                     sSchool_address=school_ms.sSchool_address,
    #                     sSchool_direct=school_ms.sSchool_direct,
    #                     sSchool_language=school_ms.sSchool_language,
    #                     isSchool=school_ms.isSchool,
    #                     sCommentary=school_ms.sCommentary,
    #                     sBin=school_ms.sBin
    #                     )
    #                 for school_ms in schools_ms if not School.objects.filter(sBin=school_ms.sBin).exists()
    #                 ]
    #         School.objects.bulk_create(schools)
    #
    #         fill_schools()
