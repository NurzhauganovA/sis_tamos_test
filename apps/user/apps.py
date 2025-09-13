from django.apps import AppConfig
from django.core.management import call_command
import sys


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.user'
