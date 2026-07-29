import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db
def test_login_success(api_client, test_user):
    response = api_client.post('/api/auth/login/', {
        'username': 'testuser',
        'password': 'testpassword123'
    })
    assert response.status_code == status.HTTP_200_OK
    assert response.data['username'] == 'testuser'
    assert response.data['role'] == 'ADMIN'


@pytest.mark.django_db
def test_login_wrong_password(api_client, test_user):
    response = api_client.post('/api/auth/login/', {
        'username': 'testuser',
        'password': 'wrongpassword'
    })
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'detail' in response.data


@pytest.mark.django_db
def test_login_non_existent_user_same_error(api_client, test_user):
    wrong_pwd_response = api_client.post('/api/auth/login/', {
        'username': 'testuser',
        'password': 'wrongpassword'
    })
    non_existent_response = api_client.post('/api/auth/login/', {
        'username': 'nonexistentuser',
        'password': 'testpassword123'
    })
    assert wrong_pwd_response.status_code == status.HTTP_400_BAD_REQUEST
    assert non_existent_response.status_code == status.HTTP_400_BAD_REQUEST
    assert wrong_pwd_response.data['detail'] == non_existent_response.data['detail']


@pytest.mark.django_db
def test_current_user_unauthenticated(api_client):
    response = api_client.get('/api/auth/me/')
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_current_user_authenticated(auth_client, test_user):
    response = auth_client.get('/api/auth/me/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['username'] == 'testuser'
    assert response.data['role'] == 'ADMIN'


@pytest.mark.django_db
def test_logout_authenticated(auth_client):
    response = auth_client.post('/api/auth/logout/')
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_user_profile_signal_creation(db):
    user = User.objects.create_user(username='signaluser', password='password123')
    assert hasattr(user, 'profile')
    assert user.profile.role == 'ADMIN'


@pytest.mark.django_db
def test_csrf_cookie_endpoint(api_client):
    response = api_client.get('/api/auth/csrf/')
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_obtain_token_valid_credentials(api_client, test_user):
    response = api_client.post('/api/auth/token/', {
        'username': 'testuser',
        'password': 'testpassword123'
    })
    assert response.status_code == status.HTTP_200_OK
    assert 'token' in response.data
    assert response.data['user']['username'] == 'testuser'
    assert response.data['user']['role'] == 'ADMIN'


@pytest.mark.django_db
def test_obtain_token_invalid_credentials(api_client, test_user):
    response = api_client.post('/api/auth/token/', {
        'username': 'testuser',
        'password': 'wrongpassword'
    })
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'token' not in response.data


@pytest.mark.django_db
def test_token_authenticated_request(api_client, test_user, default_facility):
    # Obtain token
    res_token = api_client.post('/api/auth/token/', {
        'username': 'testuser',
        'password': 'testpassword123'
    })
    token_key = res_token.data['token']

    # Make request with token in client with NO cookies/session
    from rest_framework.test import APIClient
    token_client = APIClient()
    token_client.credentials(HTTP_AUTHORIZATION=f'Token {token_key}')

    # Access a real endpoint
    res_lots = token_client.get(f'/api/lots/?facility_id={default_facility.id}')
    assert res_lots.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_token_revoke(api_client, test_user, default_facility):
    # Obtain token
    res_token = api_client.post('/api/auth/token/', {
        'username': 'testuser',
        'password': 'testpassword123'
    })
    token_key = res_token.data['token']

    from rest_framework.test import APIClient
    token_client = APIClient()
    token_client.credentials(HTTP_AUTHORIZATION=f'Token {token_key}')

    # Verify token works first
    res_lots_before = token_client.get(f'/api/lots/?facility_id={default_facility.id}')
    assert res_lots_before.status_code == status.HTTP_200_OK

    # Revoke
    res_revoke = token_client.post('/api/auth/token/revoke/')
    assert res_revoke.status_code == status.HTTP_204_NO_CONTENT

    # Verify token no longer works
    res_lots_after = token_client.get(f'/api/lots/?facility_id={default_facility.id}')
    assert res_lots_after.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_deactivate_user_deletes_token_and_blocks_access(api_client, test_user, default_facility):
    from rest_framework.authtoken.models import Token
    from apps.accounts.services import deactivate_user, create_user_account
    from apps.accounts.models import Role

    # Create a secondary user so we don't deactivate the last admin
    other_user = create_user_account(username="otheradmin", password="password123", role=Role.ADMIN)

    # Obtain token for test_user
    res_token = api_client.post('/api/auth/token/', {
        'username': 'testuser',
        'password': 'testpassword123'
    })
    token_key = res_token.data['token']

    from rest_framework.test import APIClient
    token_client = APIClient()
    token_client.credentials(HTTP_AUTHORIZATION=f'Token {token_key}')

    # Verify it works
    assert token_client.get(f'/api/lots/?facility_id={default_facility.id}').status_code == status.HTTP_200_OK

    # Deactivate test_user
    deactivate_user(user_id=test_user.id)

    # Verify token object is deleted from DB
    assert not Token.objects.filter(user=test_user).exists()

    # Verify request fails now
    res_after = token_client.get(f'/api/lots/?facility_id={default_facility.id}')
    assert res_after.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_session_auth_still_works(api_client, test_user, default_facility):
    # Log in via session
    response = api_client.post('/api/auth/login/', {
        'username': 'testuser',
        'password': 'testpassword123'
    })
    assert response.status_code == status.HTTP_200_OK

    # Make request -- session cookies should be stored in the api_client session
    res_me = api_client.get('/api/auth/me/')
    assert res_me.status_code == status.HTTP_200_OK
    assert res_me.data['username'] == 'testuser'

    # Make request to another endpoint
    res_lots = api_client.get(f'/api/lots/?facility_id={default_facility.id}')
    assert res_lots.status_code == status.HTTP_200_OK

