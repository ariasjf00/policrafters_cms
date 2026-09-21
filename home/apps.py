from django.apps import AppConfig


class HomeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "home"

    def ready(self):
        from . import wagtail_hooks  # noqa: F401
        from . import signals  # noqa: F401
