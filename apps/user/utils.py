from random import randint
from django.core.cache import cache

from apps.sms.utils import send_sms
from apps.user.models import User, UserMS, ParentMS


def _generate_activation_code():
    return randint(1000, 9999)


def send_code(user: User or UserMS or ParentMS, cache_key: str, text: str, code: int):
    try:
        if user.login.startswith('+7'):
            cache.set(f'{cache_key}_{user.login}', code, timeout=300)  # 5 min
        else:
            cache.set(f'{cache_key}_+7{user.login}', code, timeout=300)
    except AttributeError:
        if user.phone.startswith('+7'):
            cache.set(f'{cache_key}_{user.phone}', code, timeout=300)
        else:
            cache.set(f'{cache_key}_+7{user.phone}', code, timeout=300)

    try:
        if str(user.login).startswith('+7'):
            recipient = user.login
        else:
            recipient = f'+7{user.login}'
    except AttributeError:
        if str(user.phone).startswith('+7'):
            recipient = user.phone
        else:
            recipient = f'+7{user.phone}'

    send_sms(user, recipient=recipient, text=text)


def send_activation_code(user: User or UserMS or ParentMS):
    code = _generate_activation_code()
    text = f'Ваш одноразовый код: {str(code)}'

    send_code(user, 'user_activation', text, code)


def send_reset_password_code(user: User or UserMS or ParentMS):
    code = _generate_activation_code()
    text = f'Ваш одноразовый код восстановления пароля: {str(code)}'

    send_code(user, 'reset_password', text, code)
