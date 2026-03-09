from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """
    Configuration class for the accounts app.

    Every Django app has an AppConfig.
    It tells Django:
    - app name
    - where app lives
    - how to initialize it

    Here, this app will manage:
    - user accounts
    - authentication
    - roles (admin/teacher/student)
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

def ready(self):
    import accounts.signals

from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        import accounts.models