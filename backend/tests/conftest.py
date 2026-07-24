import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.facilities.models import Facility

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        username="testuser",
        password="testpassword123",
        email="testuser@example.com"
    )

@pytest.fixture
def auth_client(api_client, test_user):
    api_client.force_authenticate(user=test_user)
    return api_client

@pytest.fixture
def default_facility(db):
    # Fetch default facility seeded by migrations or create if not present
    facility, _ = Facility.objects.get_or_create(
        code="FAC-01",
        defaults={
            "name": "Default Facility",
            "address": "123 Cold Chain Road, Logistics Park"
        }
    )
    return facility
