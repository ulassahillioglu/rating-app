from django.apps import AppConfig


class CoreappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'CoreApp'

    def ready(self):
        # Import the function and call it during app initialization
        from .admin import create_support_group
        create_support_group()

    