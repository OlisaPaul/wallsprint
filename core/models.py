from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import UserManager
from django.db.models import Q

class CustomUserManager(UserManager):

    def get_by_natural_key(self, username):
        return self.get(
            Q(**{self.model.USERNAME_FIELD: username}) |
            Q(**{self.model.EMAIL_FIELD: username})
        )

# # Create your models here.
# class User(AbstractUser):
#     email = models.EmailField(unique=True)
#     objects = CustomUserManager()
