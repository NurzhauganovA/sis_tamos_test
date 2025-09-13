from rest_framework.exceptions import AuthenticationFailed
from django.utils.translation import gettext_lazy as _


class UserNotActive(AuthenticationFailed):
    default_detail = _('Ваш аккаунт временно отключен, обратитесь к менеджеру!')
    default_code = 'authentication_failed'


class UserCredentialsError(AuthenticationFailed):
    default_detail = _('Введенный логин или пароль не верен!')
    default_code = 'authentication_failed'


class UserNotFound(AuthenticationFailed):
    default_detail = _('К сожалению вы не зарегистрированы в нашей системе!')
    default_code = 'authentication_failed'


class UserPasswordNotSet(AuthenticationFailed):
    default_detail = _('Пожалуйста, восстановите свой пароль!')
    default_code = 'authentication_failed'
