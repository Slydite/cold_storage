import pytest
from rest_framework import status
from apps.parties.services import create_party

@pytest.mark.django_db
def test_unauthenticated_party_list_denied(api_client):
    response = api_client.get('/api/parties/')
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_list_parties_missing_facility_id(auth_client):
    response = auth_client.get('/api/parties/')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'facility_id' in response.data

@pytest.mark.django_db
def test_list_parties_success(auth_client, default_facility):
    create_party(facility_id=default_facility.id, name="Depositor A", type="DEPOSITOR")
    create_party(facility_id=default_facility.id, name="Vendor B", type="VENDOR")

    response = auth_client.get(f'/api/parties/?facility_id={default_facility.id}')
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2
    names = [item['name'] for item in response.data]
    assert "Depositor A" in names
    assert "Vendor B" in names

@pytest.mark.django_db
def test_list_parties_filters(auth_client, default_facility):
    create_party(facility_id=default_facility.id, name="Active Depositor", type="DEPOSITOR", is_active=True)
    create_party(facility_id=default_facility.id, name="Inactive Depositor", type="DEPOSITOR", is_active=False)
    create_party(facility_id=default_facility.id, name="Active Vendor", type="VENDOR", is_active=True)

    # Filter by type
    response = auth_client.get(f'/api/parties/?facility_id={default_facility.id}&type=DEPOSITOR')
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2
    
    # Filter by active status
    response = auth_client.get(f'/api/parties/?facility_id={default_facility.id}&is_active=false')
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]['name'] == "Inactive Depositor"

@pytest.mark.django_db
def test_create_party_api_ignores_client_code(auth_client, default_facility):
    data = {
        "facility_id": default_facility.id,
        "name": "API Transporter",
        "code": "CLIENT-SUPPLIED-CODE",  # Client-supplied code should be IGNORED
        "type": "TRANSPORTER",
        "phone": "555-0199",
        "email": "transporter@example.com",
        "address": "Terminal 1"
    }
    response = auth_client.post('/api/parties/', data)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['name'] == "Api Transporter"  # title_name sanitised
    assert response.data['code'] == "PRT-000001"  # Generated code, not CLIENT-SUPPLIED-CODE
    assert response.data['code'] != "CLIENT-SUPPLIED-CODE"
    assert response.data['type'] == "TRANSPORTER"
    assert response.data['phone'] == "555 0199"

@pytest.mark.django_db
def test_update_party_api(auth_client, default_facility):
    party = create_party(facility_id=default_facility.id, name="Depositor Original", type="DEPOSITOR")
    
    data = {
        "facility_id": default_facility.id,
        "name": "Depositor Updated Name",
        "type": "DEPOSITOR",
        "phone": "111-2222",
        "is_active": False
    }
    response = auth_client.put(f'/api/parties/{party.id}/', data)
    assert response.status_code == status.HTTP_200_OK
    assert response.data['name'] == "Depositor Updated Name"
    assert response.data['phone'] == "111 2222"
    assert response.data['is_active'] is False
    assert response.data['code'] == "PRT-000001"
