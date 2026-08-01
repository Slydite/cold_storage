import pytest
from rest_framework import status
from datetime import date
from apps.parties.services import create_party
from apps.inventory.services import create_commodity, create_grn
from apps.delivery.services import create_delivery_note
from apps.delivery.models import DeliveryNote


@pytest.fixture
def party(default_facility):
    return create_party(facility_id=default_facility.id, name="DN API Customer", type="DEPOSITOR")


@pytest.fixture
def commodity(default_facility):
    return create_commodity(facility_id=default_facility.id, name="Sweet Corn", unit="BAGS")


@pytest.fixture
def posted_grn(default_facility, party, commodity, default_block):
    return create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 25),
        items=[{
            "commodity_id": commodity.id,
            "chamber": "Chamber 1",
            "initial_qty": 500,
            "unit_weight": "40.00",
            "block_id": default_block.id,
        }]
    )


@pytest.mark.django_db
def test_unauthenticated_delivery_notes_denied(api_client):
    assert api_client.get('/api/delivery-notes/').status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    assert api_client.post('/api/delivery-notes/', {}).status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_delivery_note_api_create_list_retrieve_post(auth_client, default_facility, party, posted_grn):
    lot = posted_grn.lots.first()

    payload = {
        "facility_id": default_facility.id,
        "party_id": party.id,
        "dispatch_date": "2026-07-25",
        "vehicle_number": "KA-01-EV-4321",
        "driver_name": "Ganesh",
        "remarks": "Dispatching sweet corn",
        "lines": [
            {
                "lot_id": lot.id,
                "qty": 120
            }
        ]
    }

    # Create DN (defaults to DRAFT)
    res = auth_client.post('/api/delivery-notes/', payload, format='json')
    assert res.status_code == status.HTTP_201_CREATED
    dn_id = res.data['id']
    assert res.data['dn_number'] == "DN-000001"
    assert res.data['status'] == DeliveryNote.Status.DRAFT
    assert res.data['party_name'] == "DN Api Customer"
    assert len(res.data['lines']) == 1
    assert res.data['lines'][0]['lot_number'] == lot.lot_number
    assert res.data['lines'][0]['commodity_name'] == "Sweet Corn"

    # Stock is still 500 while DRAFT
    lot.refresh_from_db()
    assert lot.remaining_qty == 500

    # List Delivery Notes
    res_list = auth_client.get(f'/api/delivery-notes/?facility_id={default_facility.id}')
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.data) == 1

    # Retrieve single Delivery Note
    res_get = auth_client.get(f'/api/delivery-notes/{dn_id}/')
    assert res_get.status_code == status.HTTP_200_OK
    assert res_get.data['dn_number'] == "DN-000001"

    # Post Delivery Note
    res_post = auth_client.post(f'/api/delivery-notes/{dn_id}/post/')
    assert res_post.status_code == status.HTTP_200_OK
    assert res_post.data['status'] == DeliveryNote.Status.POSTED

    # Stock is now 380 after posting
    lot.refresh_from_db()
    assert lot.remaining_qty == 380


@pytest.mark.django_db
def test_delivery_note_api_cancel_draft(auth_client, default_facility, party, posted_grn):
    lot = posted_grn.lots.first()
    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=party.id,
        dispatch_date=date(2026, 7, 25),
        status=DeliveryNote.Status.DRAFT,
        lines=[{"lot_id": lot.id, "qty": 50}]
    )

    res_cancel = auth_client.post(f'/api/delivery-notes/{dn.id}/cancel/')
    assert res_cancel.status_code == status.HTTP_200_OK
    assert res_cancel.data['status'] == DeliveryNote.Status.CANCELLED

    # Posting an already cancelled note returns 400
    res_post_failed = auth_client.post(f'/api/delivery-notes/{dn.id}/post/')
    assert res_post_failed.status_code == status.HTTP_400_BAD_REQUEST
