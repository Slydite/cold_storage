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
