from django.apps import AppConfig


class FrontendApiConfig(AppConfig):
    name = 'frontend_api'
    verbose_name = 'frontend api'

    def ready(self):
        import frontend_api.models





