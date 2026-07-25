import pytest
from datetime import date
from rest_framework import status
from django.core.exceptions import ValidationError
from apps.facilities.models import Facility
from apps.locations.models import Floor, Chamber
from apps.locations.services import create_floor, create_chamber
from apps.parties.models import Party
from apps.inventory.models import Commodity, GRN, Lot
from apps.inventory.services import create_grn


@pytest.mark.django_db
def test_unauthenticated_locations_denied(api_client):
    res1 = api_client.get('/api/floors/?facility_id=1')
    assert res1.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    res2 = api_client.get('/api/chambers/')
    assert res2.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
def test_create_floor_success(auth_client, default_facility):
    data = {
        "facility_id": default_facility.id,
        "name": "Floor 1",
        "sort_order": 1
    }
    response = auth_client.post('/api/floors/', data)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['name'] == "Floor 1"
    assert response.data['facility_id'] == default_facility.id
    assert Floor.objects.filter(facility=default_facility, name="Floor 1").exists()


@pytest.mark.django_db
def test_create_floor_duplicate_name_raises(auth_client, default_facility):
    create_floor(facility_id=default_facility.id, name="Ground Floor")
    data = {
        "facility_id": default_facility.id,
        "name": "Ground Floor"
    }
    response = auth_client.post('/api/floors/', data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_chamber_success(auth_client, default_facility):
    floor = create_floor(facility_id=default_facility.id, name="Floor 1")
    data = {
        "facility_id": default_facility.id,
        "floor_id": floor.id,
        "name": "Chamber A",
        "capacity_bags": 5000
    }
    response = auth_client.post('/api/chambers/', data)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['name'] == "Chamber A"
    assert response.data['floor_id'] == floor.id
    assert response.data['facility_id'] == default_facility.id
    assert Chamber.objects.filter(floor=floor, name="Chamber A").exists()


@pytest.mark.django_db
def test_create_chamber_different_facility_raises(auth_client, default_facility):
    fac2 = Facility.objects.create(name="Facility 2", code="FAC-02")
    floor_fac2 = create_floor(facility_id=fac2.id, name="Floor Fac2")

    # Attempting to create chamber using default_facility but floor from fac2
    data = {
        "facility_id": default_facility.id,
        "floor_id": floor_fac2.id,
        "name": "Invalid Chamber"
    }
    response = auth_client.post('/api/chambers/', data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    # Direct service call should also raise ValidationError
    with pytest.raises(ValidationError):
        create_chamber(
            facility_id=default_facility.id,
            floor_id=floor_fac2.id,
            name="Invalid Chamber 2"
        )


@pytest.mark.django_db
def test_list_floors_and_chambers_filtered_by_facility(auth_client, default_facility):
    fac2 = Facility.objects.create(name="Facility 2", code="FAC-02")

    f1 = create_floor(facility_id=default_facility.id, name="F1-Floor")
    f2 = create_floor(facility_id=fac2.id, name="F2-Floor")

    c1 = create_chamber(facility_id=default_facility.id, floor_id=f1.id, name="F1-Chamber")
    c2 = create_chamber(facility_id=fac2.id, floor_id=f2.id, name="F2-Chamber")

    # Filter floors by facility
    res_f = auth_client.get(f'/api/floors/?facility_id={default_facility.id}')
    assert res_f.status_code == status.HTTP_200_OK
    floor_ids = [item['id'] for item in res_f.data]
    assert f1.id in floor_ids
    assert f2.id not in floor_ids

    # Filter chambers by facility
    res_c = auth_client.get(f'/api/chambers/?facility_id={default_facility.id}')
    assert res_c.status_code == status.HTTP_200_OK
    chamber_ids = [item['id'] for item in res_c.data]
    assert c1.id in chamber_ids
    assert c2.id not in chamber_ids


@pytest.mark.django_db
def test_create_grn_with_valid_chamber_id(auth_client, default_facility):
    party = Party.objects.create(facility=default_facility, name="Farmer Ramesh", code="P01", type="DEPOSITOR")
    commodity = Commodity.objects.create(facility=default_facility, name="Potatoes", code="POT")
    floor = create_floor(facility_id=default_facility.id, name="Floor 2")
    chamber = create_chamber(facility_id=default_facility.id, floor_id=floor.id, name="Chamber 4")

    data = {
        "facility_id": default_facility.id,
        "party_id": party.id,
        "receipt_date": str(date.today()),
        "items": [
            {
                "commodity_id": commodity.id,
                "chamber_id": chamber.id,
                "initial_qty": 100
            }
        ]
    }
    response = auth_client.post('/api/grns/', data, format='json')
    assert response.status_code == status.HTTP_201_CREATED

    lot_data = response.data['lots'][0]
    assert lot_data['chamber_ref_id'] == chamber.id
    assert lot_data['floor_ref_id'] == floor.id
    assert lot_data['chamber'] == "Chamber 4"
    assert lot_data['floor'] == "Floor 2"

    lot_obj = Lot.objects.get(pk=lot_data['id'])
    assert lot_obj.chamber_ref == chamber
    assert lot_obj.floor_ref == floor
    assert lot_obj.chamber == "Chamber 4"
    assert lot_obj.floor == "Floor 2"


@pytest.mark.django_db
def test_create_grn_with_chamber_id_different_facility_raises(default_facility):
    fac2 = Facility.objects.create(name="Facility 2", code="FAC-02")
    party = Party.objects.create(facility=default_facility, name="Farmer Ramesh", code="P01", type="DEPOSITOR")
    commodity = Commodity.objects.create(facility=default_facility, name="Potatoes", code="POT")

    floor_fac2 = create_floor(facility_id=fac2.id, name="Floor Fac2")
    chamber_fac2 = create_chamber(facility_id=fac2.id, floor_id=floor_fac2.id, name="Chamber Fac2")

    with pytest.raises(ValidationError):
        create_grn(
            facility_id=default_facility.id,
            party_id=party.id,
            receipt_date=date.today(),
            items=[
                {
                    "commodity_id": commodity.id,
                    "chamber_id": chamber_fac2.id,
                    "initial_qty": 50
                }
            ]
        )
