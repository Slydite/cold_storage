from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ValidationError


def login_user(*, request, username: str, password: str):
    user = authenticate(request=request, username=username, password=password)
    if user is None or not user.is_active:
        raise ValidationError("Invalid username or password.")
    login(request, user)
    return user


def logout_user(*, request) -> None:
    logout(request)
