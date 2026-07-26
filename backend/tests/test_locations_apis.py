import pytest
from datetime import date
from rest_framework import status
from django.core.exceptions import ValidationError
from apps.facilities.models import Facility
from apps.locations.models import Chamber, Floor, Block
from apps.locations.services import create_chamber, create_floor, create_block
from apps.parties.models import Party
from apps.inventory.models import Commodity, GRN, Lot
from apps.inventory.services import create_grn


@pytest.mark.django_db
def test_unauthenticated_locations_denied(api_client):
    res1 = api_client.get('/api/chambers/')
    assert res1.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    res2 = api_client.get('/api/floors/')
    assert res2.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    res3 = api_client.get('/api/blocks/')
    assert res3.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
def test_create_chamber_floor_block_hierarchy_success(auth_client, default_facility):
    # Create Chamber
    chamber_res = auth_client.post('/api/chambers/', {
        "facility_id": default_facility.id,
        "name": "Chamber 1",
        "sort_order": 1
    })
    assert chamber_res.status_code == status.HTTP_201_CREATED
    chamber_id = chamber_res.data['id']
    assert chamber_res.data['name'] == "Chamber 1"
    assert chamber_res.data['facility_id'] == default_facility.id

    # Create Floor under Chamber
    floor_res = auth_client.post('/api/floors/', {
        "chamber_id": chamber_id,
        "name": "Floor 1",
        "sort_order": 1
    })
    assert floor_res.status_code == status.HTTP_201_CREATED
    floor_id = floor_res.data['id']
    assert floor_res.data['name'] == "Floor 1"
    assert floor_res.data['chamber_id'] == chamber_id
    assert floor_res.data['facility_id'] == default_facility.id

    # Create Block under Floor
    block_res = auth_client.post('/api/blocks/', {
        "floor_id": floor_id,
        "name": "Block A",
        "capacity_bags": 5000,
        "sort_order": 1
    })
    assert block_res.status_code == status.HTTP_201_CREATED
    block_id = block_res.data['id']
    assert block_res.data['name'] == "Block A"
    assert block_res.data['floor_id'] == floor_id
    assert block_res.data['chamber_id'] == chamber_id
    assert block_res.data['facility_id'] == default_facility.id

    # Read back chain
    block_obj = Block.objects.select_related('floor__chamber__facility').get(pk=block_id)
    assert block_obj.floor.id == floor_id
    assert block_obj.floor.chamber.id == chamber_id
    assert block_obj.floor.chamber.facility.id == default_facility.id
    assert str(block_obj) == "Chamber 1 / Floor 1 / Block A"


@pytest.mark.django_db
def test_create_floor_different_facility_chamber_raises(auth_client, default_facility):
    fac2 = Facility.objects.create(name="Facility 2", code="FAC-02")
    chamber_fac2 = create_chamber(facility_id=fac2.id, name="Chamber Fac2")

    # API call providing default_facility but chamber from fac2
    response = auth_client.post('/api/floors/', {
        "facility_id": default_facility.id,
        "chamber_id": chamber_fac2.id,
        "name": "Invalid Floor"
    })
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    # Service call should also raise ValidationError
    with pytest.raises(ValidationError):
        create_floor(
            facility_id=default_facility.id,
            chamber_id=chamber_fac2.id,
            name="Invalid Floor Service"
        )


@pytest.mark.django_db
def test_create_block_different_chamber_floor_raises(auth_client, default_facility):
    chamber1 = create_chamber(facility_id=default_facility.id, name="Chamber 1")
    chamber2 = create_chamber(facility_id=default_facility.id, name="Chamber 2")
    floor_ch2 = create_floor(chamber_id=chamber2.id, name="Floor in Ch2")

    # Attempting to create block with chamber_id=chamber1 but floor belonging to chamber2
    response = auth_client.post('/api/blocks/', {
        "chamber_id": chamber1.id,
        "floor_id": floor_ch2.id,
        "name": "Mismatched Block"
    })
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    with pytest.raises(ValidationError):
        create_block(
            chamber_id=chamber1.id,
            floor_id=floor_ch2.id,
            name="Mismatched Block Service"
        )


@pytest.mark.django_db
def test_create_grn_with_mismatched_location_chain_raises(default_facility):
    fac2 = Facility.objects.create(name="Facility 2", code="FAC-02")
    party = Party.objects.create(facility=default_facility, name="Farmer Ramesh", code="P01", type="DEPOSITOR")
    commodity = Commodity.objects.create(facility=default_facility, name="Potatoes", code="POT")

    chamber_fac2 = create_chamber(facility_id=fac2.id, name="Chamber Fac2")
    floor_fac2 = create_floor(chamber_id=chamber_fac2.id, name="Floor Fac2")
    block_fac2 = create_block(floor_id=floor_fac2.id, name="Block Fac2")

    # 1. Block belonging to a different facility
    with pytest.raises(ValidationError) as exc_info:
        create_grn(
            facility_id=default_facility.id,
            party_id=party.id,
            receipt_date=date.today(),
            items=[
                {
                    "commodity_id": commodity.id,
                    "block_id": block_fac2.id,
                    "initial_qty": 50
                }
            ]
        )
    assert "does not belong to facility" in str(exc_info.value)

    # 2. Mismatched chamber_id and block's actual floor/chamber
    chamber1 = create_chamber(facility_id=default_facility.id, name="Chamber 1")
    chamber2 = create_chamber(facility_id=default_facility.id, name="Chamber 2")
    floor1 = create_floor(chamber_id=chamber1.id, name="Floor 1")
    block1 = create_block(floor_id=floor1.id, name="Block 1")

    with pytest.raises(ValidationError) as exc_info2:
        create_grn(
            facility_id=default_facility.id,
            party_id=party.id,
            receipt_date=date.today(),
            items=[
                {
                    "commodity_id": commodity.id,
                    "chamber_id": chamber2.id,
                    "floor_id": floor1.id,
                    "block_id": block1.id,
                    "initial_qty": 50
                }
            ]
        )
    assert "does not belong to chamber" in str(exc_info2.value) or "does not belong to floor" in str(exc_info2.value)


@pytest.mark.django_db
def test_create_grn_with_valid_location_chain_populates_refs_and_text(auth_client, default_facility):
    party = Party.objects.create(facility=default_facility, name="Farmer Ramesh", code="P01", type="DEPOSITOR")
    commodity = Commodity.objects.create(facility=default_facility, name="Potatoes", code="POT")

    chamber = create_chamber(facility_id=default_facility.id, name="Chamber 4")
    floor = create_floor(chamber_id=chamber.id, name="Floor 2")
    block = create_block(floor_id=floor.id, name="Block 9")

    data = {
        "facility_id": default_facility.id,
        "party_id": party.id,
        "receipt_date": str(date.today()),
        "items": [
            {
                "commodity_id": commodity.id,
                "chamber_id": chamber.id,
                "floor_id": floor.id,
                "block_id": block.id,
                "initial_qty": 100
            }
        ]
    }
    response = auth_client.post('/api/grns/', data, format='json')
    assert response.status_code == status.HTTP_201_CREATED

    lot_data = response.data['lots'][0]
    assert lot_data['chamber_ref_id'] == chamber.id
    assert lot_data['chamber_name'] == "Chamber 4"
    assert lot_data['floor_ref_id'] == floor.id
    assert lot_data['floor_name'] == "Floor 2"
    assert lot_data['block_ref_id'] == block.id
    assert lot_data['block_name'] == "Block 9"
    assert lot_data['chamber'] == "Chamber 4"
    assert lot_data['floor'] == "Floor 2"

    lot_obj = Lot.objects.get(pk=lot_data['id'])
    assert lot_obj.chamber_ref == chamber
    assert lot_obj.floor_ref == floor
    assert lot_obj.block_ref == block
    assert lot_obj.chamber == "Chamber 4"
    assert lot_obj.floor == "Floor 2"


@pytest.mark.django_db
def test_list_blocks_filtered_by_facility(auth_client, default_facility):
    fac2 = Facility.objects.create(name="Facility 2", code="FAC-02")

    ch1 = create_chamber(facility_id=default_facility.id, name="F1-Chamber")
    f1 = create_floor(chamber_id=ch1.id, name="F1-Floor")
    b1 = create_block(floor_id=f1.id, name="F1-Block")

    ch2 = create_chamber(facility_id=fac2.id, name="F2-Chamber")
    f2 = create_floor(chamber_id=ch2.id, name="F2-Floor")
    b2 = create_block(floor_id=f2.id, name="F2-Block")

    # Filter blocks by facility
    res_b = auth_client.get(f'/api/blocks/?facility_id={default_facility.id}')
    assert res_b.status_code == status.HTTP_200_OK
    block_ids = [item['id'] for item in res_b.data]
    assert b1.id in block_ids
    assert b2.id not in block_ids

