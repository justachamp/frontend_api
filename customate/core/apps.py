import logging

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from core.logger import CustomateLogger
        logging.setLoggerClass(CustomateLogger)
