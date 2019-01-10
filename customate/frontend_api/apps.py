from django.apps import AppConfig


class FrontendApiConfig(AppConfig):
    name = 'frontend_api'

    def ready(self):
        import frontend_api.signals
