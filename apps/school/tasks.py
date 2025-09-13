from datetime import datetime, timedelta
from django.utils import timezone
from .models import Class
from celery import shared_task


now_year = timezone.now().year


def increment_class_num(school_class):
    """ Увеличивает номер класса на 1, если класс не последний. """

    if int(school_class.class_num) < school_class.max_class_num:
        school_class.class_num += 1
    else:
        school_class.class_num = school_class.max_class_num
        school_class.isGraduated = True
    return school_class


@shared_task(run_every=datetime(now_year, 6, 16))
def update_classes():
    """ Обновляет классы в определенный день. """

    classes = Class.objects.all()

    for school_class in classes:
        if (timezone.now() - school_class.modified) >= timedelta(days=365):
            increment_class_num(school_class)
            school_class.save()


print(update_classes())
