import pytest
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.accounts.models import UserProfile, Role
from apps.accounts.services import (
    create_user_account,
    update_user_account,
    deactivate_user
)

User = get_user_model()


@pytest.mark.django_db
def test_create_user_account_hashes_password_and_sets_role():
    user = create_user_account(
        username="newmanager",
        password="secretpassword123",
        email="manager@example.com",
        first_name="Jane",
        last_name="Doe",
        role=Role.ADMIN
    )
    assert user.username == "newmanager"
    assert user.check_password("secretpassword123") is True
    assert user.password != "secretpassword123"  # Password is encrypted/hashed
    assert user.profile.role == Role.ADMIN
    assert user.is_active is True


@pytest.mark.django_db
def test_create_user_duplicate_username_raises():
    create_user_account(username="duplicateuser", password="password123")

    with pytest.raises(ValidationError):
        create_user_account(username="duplicateuser", password="password456")


@pytest.mark.django_db
def test_update_user_account_password_rehashes_and_role_updates():
    user = create_user_account(username="updateuser", password="oldpassword123", role=Role.ADMIN)

    updated_user = update_user_account(
        user_id=user.id,
        first_name="UpdatedName",
        password="newpassword456"
    )

    assert updated_user.first_name == "UpdatedName"
    assert updated_user.check_password("newpassword456") is True
    assert updated_user.check_password("oldpassword123") is False


@pytest.mark.django_db
def test_deactivate_user_success_and_last_admin_protection():
    admin1 = create_user_account(username="admin1", password="password123", role=Role.ADMIN)
    admin2 = create_user_account(username="admin2", password="password123", role=Role.ADMIN)

    # Deactivating admin1 should succeed because admin2 is still active
    deactivated = deactivate_user(user_id=admin1.id)
    assert deactivated.is_active is False

    # Deactivating admin2 (the last active admin) should raise ValidationError
    with pytest.raises(ValidationError, match="Cannot deactivate the only remaining active administrator."):
        deactivate_user(user_id=admin2.id)


@pytest.mark.django_db
def test_user_viewset_api_flow(auth_client, test_user):
    # Make test_user an admin profile
    UserProfile.objects.get_or_create(user=test_user, defaults={'role': Role.ADMIN})

    # 1. Create user via API
    data = {
        "username": "apiuser",
        "password": "apipassword123",
        "email": "api@example.com",
        "role": Role.ADMIN
    }
    create_res = auth_client.post('/api/users/', data)
    assert create_res.status_code == status.HTTP_201_CREATED
    user_id = create_res.data['id']
    assert create_res.data['username'] == "apiuser"

    # Verify password was hashed
    created_db_user = User.objects.get(pk=user_id)
    assert created_db_user.check_password("apipassword123") is True

    # 2. List users
    list_res = auth_client.get('/api/users/')
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.data) >= 2

    # 3. Update user
    update_data = {
        "first_name": "API",
        "last_name": "User"
    }
    update_res = auth_client.put(f'/api/users/{user_id}/', update_data)
    assert update_res.status_code == status.HTTP_200_OK
    assert update_res.data['first_name'] == "API"
    # Regression: DRF's BooleanField coerces an ABSENT value to False for
    # form/multipart input. When `is_active` was accepted by the update
    # serializer, a PUT that only renamed a user arrived with is_active=False
    # and silently deactivated the account. Renaming must never do that.
    assert update_res.data['is_active'] is True

    # 4. Deactivate user via action endpoint
    deact_res = auth_client.post(f'/api/users/{user_id}/deactivate/')
    assert deact_res.status_code == status.HTTP_200_OK
    assert deact_res.data['is_active'] is False

    # 5. Re-activate via the counterpart action
    act_res = auth_client.post(f'/api/users/{user_id}/activate/')
    assert act_res.status_code == status.HTTP_200_OK
    assert act_res.data['is_active'] is True
