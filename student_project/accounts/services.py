from django.contrib.auth import authenticate
from accounts.models import User


def authenticate_user(username, password):
    return authenticate(username=username, password=password)


def get_user_profile(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None