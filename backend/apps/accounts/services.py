from django.contrib.auth import authenticate, login, logout, get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from .models import UserProfile, Role

User = get_user_model()


def login_user(*, request, username: str, password: str):
    user = authenticate(request=request, username=username, password=password)
    if user is None or not user.is_active:
        raise ValidationError("Invalid username or password.")
    login(request, user)
    return user


def logout_user(*, request) -> None:
    logout(request)


@transaction.atomic
def create_user_account(
    *,
    username: str,
    password: str,
    email: str = '',
    first_name: str = '',
    last_name: str = '',
    role: str = Role.ADMIN,
    is_active: bool = True
) -> User:
    """
    Create a new user account with hashed password and UserProfile role.
    """
    if User.objects.filter(username=username).exists():
        raise ValidationError(f"Username '{username}' is already taken.")

    user = User.objects.create_user(
        username=username,
        password=password,
        email=email,
        first_name=first_name,
        last_name=last_name,
        is_active=is_active
    )

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role = role
    profile.save()

    return user


@transaction.atomic
def update_user_account(*, user_id: int, **fields) -> User:
    """
    Update an existing user account.
    """
    try:
        user = User.objects.select_related('profile').get(pk=user_id)
    except User.DoesNotExist:
        raise ValidationError(f"User with ID {user_id} does not exist.")

    # `is_active` is intentionally not updatable here -- see
    # UserUpdateInputSerializer for why. Use activate_user/deactivate_user.
    allowed_user_fields = ['email', 'first_name', 'last_name']
    for field in allowed_user_fields:
        if field in fields and fields[field] is not None:
            setattr(user, field, fields[field])

    if 'password' in fields and fields['password']:
        user.set_password(fields['password'])

    user.full_clean()
    user.save()

    if 'role' in fields and fields['role']:
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = fields['role']
        profile.save()

    return user


@transaction.atomic
def deactivate_user(*, user_id: int) -> User:
    """
    Deactivate a user account. Refuses to deactivate the last active superuser/admin.
    """
    try:
        user = User.objects.select_related('profile').get(pk=user_id)
    except User.DoesNotExist:
        raise ValidationError(f"User with ID {user_id} does not exist.")

    if not user.is_active:
        return user

    is_admin_user = user.is_superuser or (hasattr(user, 'profile') and user.profile.role == Role.ADMIN)
    if is_admin_user:
        active_admin_count = User.objects.filter(is_active=True).filter(
            Q(is_superuser=True) | Q(profile__role=Role.ADMIN)
        ).distinct().count()
        if active_admin_count <= 1:
            raise ValidationError("Cannot deactivate the only remaining active administrator.")

    user.is_active = False
    user.save()

    from rest_framework.authtoken.models import Token
    Token.objects.filter(user=user).delete()

    return user


@transaction.atomic
def activate_user(*, user_id: int) -> User:
    """
    Re-activate a previously deactivated user account. No guard needed --
    adding an active user can never lock anyone out.
    """
    try:
        user = User.objects.select_related('profile').get(pk=user_id)
    except User.DoesNotExist:
        raise ValidationError(f"User with ID {user_id} does not exist.")

    if user.is_active:
        return user

    user.is_active = True
    user.save()
    return user


@transaction.atomic
def get_or_create_user_token(*, username: str, password: str) -> tuple[str, User]:
    """
    Authenticate a user with credentials and return/create their auth token.
    """
    user = authenticate(username=username, password=password)
    if user is None or not user.is_active:
        raise ValidationError("Invalid username or password.")

    from rest_framework.authtoken.models import Token
    token, _ = Token.objects.get_or_create(user=user)
    return token.key, user


@transaction.atomic
def revoke_user_token(*, user: User) -> None:
    """
    Revoke (delete) the auth token for the given user.
    """
    from rest_framework.authtoken.models import Token
    Token.objects.filter(user=user).delete()


