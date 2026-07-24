import pytest
from rest_framework import status
from datetime import date
from apps.parties.services import create_party
from apps.inventory.services import create_commodity, create_grn

@pytest.fixture
def party(default_facility):
    return create_party(facility_id=default_facility.id, name="API Farmer", code="FARM-API", type="DEPOSITOR")

@pytest.fixture
def commodity(default_facility):
    return create_commodity(facility_id=default_facility.id, name="Onion", code="ONI-01", unit="BAGS")

@pytest.mark.django_db
def test_unauthenticated_inventory_denied(api_client):
    assert api_client.get('/api/commodities/').status_code == status.HTTP_403_FORBIDDEN
    assert api_client.get('/api/grns/').status_code == status.HTTP_403_FORBIDDEN
    assert api_client.get('/api/lots/').status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_commodity_api_lifecycle(auth_client, default_facility):
    # Create commodity
    data = {
        "facility_id": default_facility.id,
        "name": "Carrot",
        "code": "CAR-01",
        "unit": "BAGS",
        "description": "Orange carrots"
    }
    res = auth_client.post('/api/commodities/', data)
    assert res.status_code == status.HTTP_201_CREATED
    comm_id = res.data['id']
    assert res.data['name'] == "Carrot"

    # List commodities
    res_list = auth_client.get(f'/api/commodities/?facility_id={default_facility.id}')
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.data) == 1

    # Update commodity
    update_data = {
        "facility_id": default_facility.id,
        "name": "Red Carrot",
        "code": "CAR-01",
        "unit": "BAGS",
        "is_active": True
    }
    res_upd = auth_client.put(f'/api/commodities/{comm_id}/', update_data)
    assert res_upd.status_code == status.HTTP_200_OK
    assert res_upd.data['name'] == "Red Carrot"

@pytest.mark.django_db
def test_grn_api_create_and_list(auth_client, default_facility, party, commodity):
    grn_payload = {
        "facility_id": default_facility.id,
        "party_id": party.id,
        "receipt_date": "2026-07-25",
        "vehicle_number": "KA-05-MN-9999",
        "driver_name": "Suresh",
        "remarks": "First batch of onions",
        "items": [
            {
                "commodity_id": commodity.id,
                "chamber": "Chamber 1",
                "floor": "Floor 2",
                "initial_qty": 300,
                "unit_weight": "40.00",
                "rent_rate_per_unit": "10.00"
            }
        ]
    }

    res = auth_client.post('/api/grns/', grn_payload, format='json')
    assert res.status_code == status.HTTP_201_CREATED
    assert res.data['grn_number'] == "GRN-000001"
    assert res.data['party_name'] == "API Farmer"
    assert len(res.data['lots']) == 1
    assert res.data['lots'][0]['remaining_qty'] == 300

    # List GRNs
    res_list = auth_client.get(f'/api/grns/?facility_id={default_facility.id}')
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.data) == 1

@pytest.mark.django_db
def test_lot_api_withdraw(auth_client, default_facility, party, commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 25),
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 500,
            "chamber": "Chamber 3"
        }]
    )
    lot_id = grn.lots.first().id

    # List lots
    res_lots = auth_client.get(f'/api/lots/?facility_id={default_facility.id}&in_stock_only=true')
    assert res_lots.status_code == status.HTTP_200_OK
    assert len(res_lots.data) == 1
    assert res_lots.data[0]['remaining_qty'] == 500

    # Withdraw 150 units via action
    withdraw_res = auth_client.post(f'/api/lots/{lot_id}/withdraw/', {"qty": 150})
    assert withdraw_res.status_code == status.HTTP_200_OK
    assert withdraw_res.data['remaining_qty'] == 350
