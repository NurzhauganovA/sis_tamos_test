from random import randint

import requests
from django.conf import settings

from apps.user.models import User, UserMS, ParentMS


def _gen_sms_id(user: User or UserMS or ParentMS):
    try:
        school_id = [school for school in user.school.all()]

        school = ''
        for i in school_id[::-1]:
            school += str(i.id)
    except AttributeError:
        school = '0'
    user_id = user.pk
    random_num = randint(1000, 9999)

    result = int(f'{school}{user_id}{random_num}')

    return result


def send_sms(user: User or UserMS or ParentMS, recipient: str, text: str):
    sms_id = _gen_sms_id(user)

    url = 'http://service.sms-consult.kz/get.ashx'

    params = {
        'login': settings.SMS_CREDENTIALS.get('LOGIN'),
        'password': settings.SMS_CREDENTIALS.get('PASSWORD'),
        'type': 'message',
        'id': sms_id,
        'sender': settings.SMS_CREDENTIALS.get('SENDER'),
        'recipient': recipient,
        'text': text
    }

    resp = requests.get(url=url, params=params)

    if resp.text == 'status=100':
        return True
    return False
