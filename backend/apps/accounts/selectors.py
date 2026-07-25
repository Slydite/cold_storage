from django.contrib.auth import get_user_model
from django.db.models import QuerySet

User = get_user_model()


def get_users_list(is_active: bool = None) -> QuerySet[User]:
    """
    Fetch all users ordered by username, with preloaded profile.
    """
    qs = User.objects.select_related('profile')
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs.order_by('username')


def get_user_by_id(user_id: int) -> User:
    """
    Fetch a user by ID with preloaded profile.
    """
    return User.objects.select_related('profile').get(pk=user_id)
