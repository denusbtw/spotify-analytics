from django.contrib.auth.models import AbstractUser

from spotify_analytics.core.models import UUIDModel


class User(UUIDModel, AbstractUser):
    pass
