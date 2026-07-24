import pytest
from rest_framework import status
from apps.facilities.models import Facility

@pytest.mark.django_db
def test_unauthenticated_facility_list_denied(api_client):
    response = api_client.get('/api/facilities/')
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_list_facilities_authenticated(auth_client, default_facility):
    response = auth_client.get('/api/facilities/')
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) >= 1
    codes = [item['code'] for item in response.data]
    assert default_facility.code in codes

@pytest.mark.django_db
def test_retrieve_facility(auth_client, default_facility):
    response = auth_client.get(f'/api/facilities/{default_facility.id}/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['name'] == default_facility.name
    assert response.data['code'] == default_facility.code

@pytest.mark.django_db
def test_create_facility_api(auth_client):
    data = {
        "name": "New API Facility",
        "code": "API-01",
        "address": "API Logistics Area"
    }
    response = auth_client.post('/api/facilities/', data)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['name'] == "New API Facility"
    assert response.data['code'] == "API-01"

@pytest.mark.django_db
def test_update_facility_api(auth_client, default_facility):
    data = {
        "name": "Updated Facility Name",
        "code": default_facility.code,
        "address": "Updated Address"
    }
    response = auth_client.put(f'/api/facilities/{default_facility.id}/', data)
    assert response.status_code == status.HTTP_200_OK
    assert response.data['name'] == "Updated Facility Name"
    assert response.data['address'] == "Updated Address"
