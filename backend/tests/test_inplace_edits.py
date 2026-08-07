import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APIClient

from apps.parties.services import create_party
from apps.inventory.services import create_commodity, create_grn, update_grn, post_grn
from apps.inventory.models import GRN, Lot
from apps.delivery.services import create_delivery_note, update_delivery_note, post_delivery_note
from apps.delivery.models import DeliveryNote, DeliveryLine

@pytest.fixture
def party(default_facility):
    return create_party(facility_id=default_facility.id, name="Test Farmer", type="DEPOSITOR")

@pytest.fixture
def commodity(default_facility):
    return create_commodity(facility_id=default_facility.id, name="Potato", unit="BAGS")

def get_serial_from_lot_number(lot_number):
    parts = lot_number.split('-')
    return parts[1]

# 1. editing a DRAFT GRN updates header fields and keeps grn_number unchanged
@pytest.mark.django_db
def test_update_grn_header_and_grn_number(default_facility, party, commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 8, 7),
        status=GRN.Status.DRAFT,
        vehicle_number="KA-01-1234",
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id
        }]
    )
    original_grn_number = grn.grn_number
    
    updated_grn = update_grn(
        grn_id=grn.id,
        vehicle_number="MH-02-5678",
        remarks="Updated remarks",
        receipt_date=date(2026, 8, 8)
    )
    
    assert updated_grn.grn_number == original_grn_number
    assert updated_grn.vehicle_number == "MH-02-5678"
    assert updated_grn.remarks == "Updated remarks"
    assert updated_grn.receipt_date == date(2026, 8, 8)

# 2. changing a line's quantity rebuilds only the bags part; the serial is identical before and after
@pytest.mark.django_db
def test_update_grn_qty_rebuilds_bags_keeps_serial(default_facility, party, commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 8, 7),
        status=GRN.Status.DRAFT,
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id
        }]
    )
    lot = grn.lots.first()
    original_lot_number = lot.lot_number
    original_serial = get_serial_from_lot_number(original_lot_number)
    
    update_grn(
        grn_id=grn.id,
        items=[{
            "id": lot.id,
            "commodity_id": commodity.id,
            "initial_qty": 150,
            "block_id": default_block.id
        }]
    )
    
    lot.refresh_from_db()
    new_lot_number = lot.lot_number
    new_serial = get_serial_from_lot_number(new_lot_number)
    
    assert original_serial == new_serial
    assert new_lot_number.endswith("-00150")

# 3. changing the receipt date rebuilds the date part, serial unchanged
@pytest.mark.django_db
def test_update_grn_receipt_date_rebuilds_date_keeps_serial(default_facility, party, commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 8, 7),
        status=GRN.Status.DRAFT,
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id
        }]
    )
    lot = grn.lots.first()
    original_lot_number = lot.lot_number
    original_serial = get_serial_from_lot_number(original_lot_number)
    
    update_grn(
        grn_id=grn.id,
        receipt_date=date(2026, 8, 9),
        items=[{
            "id": lot.id,
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id
        }]
    )
    
    lot.refresh_from_db()
    new_lot_number = lot.lot_number
    new_serial = get_serial_from_lot_number(new_lot_number)
    
    assert original_serial == new_serial
    assert new_lot_number.startswith("20260809-")

# 4. adding a line issues a new serial; removing one deletes the lot and does not reuse its serial on the next addition
@pytest.mark.django_db
def test_update_grn_add_and_remove_lines_serials(default_facility, party, commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 8, 7),
        status=GRN.Status.DRAFT,
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id
        }]
    )
    lot1 = grn.lots.first()
    lot1_serial = get_serial_from_lot_number(lot1.lot_number)
    
    update_grn(
        grn_id=grn.id,
        items=[
            {
                "id": lot1.id,
                "commodity_id": commodity.id,
                "initial_qty": 100,
                "block_id": default_block.id
            },
            {
                "commodity_id": commodity.id,
                "initial_qty": 50,
                "block_id": default_block.id
            }
        ]
    )
    
    lots = list(grn.lots.order_by('id'))
    assert len(lots) == 2
    lot2 = lots[1]
    lot2_serial = get_serial_from_lot_number(lot2.lot_number)
    assert lot1_serial != lot2_serial
    
    update_grn(
        grn_id=grn.id,
        items=[
            {
                "id": lot2.id,
                "commodity_id": commodity.id,
                "initial_qty": 50,
                "block_id": default_block.id
            },
            {
                "commodity_id": commodity.id,
                "initial_qty": 200,
                "block_id": default_block.id
            }
        ]
    )
    
    assert not Lot.objects.filter(id=lot1.id).exists()
    lots_after = list(grn.lots.order_by('id'))
    assert len(lots_after) == 2
    
    lot3 = lots_after[1]
    lot3_serial = get_serial_from_lot_number(lot3.lot_number)
    
    assert lot3_serial != lot1_serial
    assert lot3_serial != lot2_serial

# 5. a lot with delivery lines against it cannot be removed
@pytest.mark.django_db
def test_update_grn_cannot_remove_lot_with_delivery_lines(default_facility, party, commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 8, 7),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id
        }]
    )
    lot = grn.lots.first()
    
    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=party.id,
        dispatch_date=date(2026, 8, 8),
        status=DeliveryNote.Status.DRAFT,
        lines=[{
            "lot_id": lot.id,
            "qty": 40
        }]
    )
    
    grn.status = GRN.Status.DRAFT
    grn.save()
    
    with pytest.raises(ValidationError) as excinfo:
        update_grn(
            grn_id=grn.id,
            items=[]
        )
    assert dn.dn_number in str(excinfo.value)

# 6. editing a POSTED GRN is rejected; likewise CANCELLED
@pytest.mark.django_db
def test_update_grn_rejected_for_posted_or_cancelled(default_facility, party, commodity, default_block):
    grn_posted = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 8, 7),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id
        }]
    )
    with pytest.raises(ValidationError) as excinfo:
        update_grn(grn_id=grn_posted.id, remarks="Change posted")
    assert "POSTED" in str(excinfo.value)
    
    grn_cancelled = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 8, 7),
        status=GRN.Status.CANCELLED,
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id
        }]
    )
    with pytest.raises(ValidationError) as excinfo:
        update_grn(grn_id=grn_cancelled.id, remarks="Change cancelled")
    assert "CANCELLED" in str(excinfo.value)

# 7. update-and-post applies changes and posts in one step
@pytest.mark.django_db
def test_update_and_post_grn_api(auth_client, default_facility, party, commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 8, 7),
        status=GRN.Status.DRAFT,
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id
        }]
    )
    
    payload = {
        "remarks": "Updated remarks through API",
        "items": [{
            "id": grn.lots.first().id,
            "commodity_id": commodity.id,
            "initial_qty": 120,
            "block_id": default_block.id
        }]
    }
    
    res = auth_client.post(f"/api/grns/{grn.id}/update-and-post/", payload, format="json")
    assert res.status_code == status.HTTP_200_OK
    
    grn.refresh_from_db()
    assert grn.status == GRN.Status.POSTED
    assert grn.remarks == "Updated remarks through API"
    assert grn.lots.first().initial_qty == 120

# 8. update-and-post that fails at the post step leaves the draft completely unchanged
@pytest.mark.django_db
def test_update_and_post_grn_api_rollback_on_post_failure(auth_client, default_facility, party, commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 8, 7),
        status=GRN.Status.DRAFT,
        remarks="Original remarks",
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id
        }]
    )
    original_lot_qty = grn.lots.first().initial_qty
    
    payload = {
        "remarks": "Attempted update remarks",
        "items": [{
            "id": grn.lots.first().id,
            "commodity_id": commodity.id,
            "initial_qty": 130,
            "block_id": default_block.id
        }]
    }
    
    with patch('apps.inventory.views.post_grn', side_effect=ValidationError("Mocked post failure")):
        res = auth_client.post(f"/api/grns/{grn.id}/update-and-post/", payload, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        
    grn.refresh_from_db()
    assert grn.status == GRN.Status.DRAFT
    assert grn.remarks == "Original remarks"
    assert grn.lots.first().initial_qty == original_lot_qty

# 9. the same set for delivery notes, plus: editing a draft note changes no lot's remaining_qty
@pytest.mark.django_db
def test_update_delivery_note_lifecycle(default_facility, party, commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 8, 7),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id
        }]
    )
    lot = grn.lots.first()
    
    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=party.id,
        dispatch_date=date(2026, 8, 8),
        status=DeliveryNote.Status.DRAFT,
        lines=[{
            "lot_id": lot.id,
            "qty": 30
        }]
    )
    
    lot.refresh_from_db()
    assert lot.remaining_qty == 100
    
    update_delivery_note(
        delivery_note_id=dn.id,
        vehicle_number="MH-12-1234",
        lines=[{
            "lot_id": lot.id,
            "qty": 50
        }]
    )
    
    dn.refresh_from_db()
    assert dn.vehicle_number == "MH-12-1234"
    assert dn.lines.first().qty == 50
    
    lot.refresh_from_db()
    assert lot.remaining_qty == 100

# 10. a lot number that is not in the current format is left untouched by an edit
@pytest.mark.django_db
def test_legacy_lot_number_untouched(default_facility, party, commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 8, 7),
        status=GRN.Status.DRAFT,
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id,
            "lot_number": "LEGACY-LOT-123"
        }],
        validate_lot_number_format=False
    )
    lot = grn.lots.first()
    assert lot.lot_number == "LEGACY-LOT-123"
    
    update_grn(
        grn_id=grn.id,
        receipt_date=date(2026, 8, 9),
        items=[{
            "id": lot.id,
            "commodity_id": commodity.id,
            "initial_qty": 150,
            "block_id": default_block.id
        }]
    )
    
    lot.refresh_from_db()
    assert lot.lot_number == "LEGACY-LOT-123"

# 11. both endpoints require authentication
@pytest.mark.django_db
def test_endpoints_require_authentication(default_facility, party, commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 8, 7),
        status=GRN.Status.DRAFT,
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id
        }]
    )
    
    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=party.id,
        dispatch_date=date(2026, 8, 8),
        status=DeliveryNote.Status.DRAFT,
        lines=[{
            "lot_id": grn.lots.first().id,
            "qty": 30
        }]
    )
    
    unauth_client = APIClient()
    
    res = unauth_client.patch(f"/api/grns/{grn.id}/", {"remarks": "Anon update"})
    assert res.status_code == status.HTTP_403_FORBIDDEN
    
    res = unauth_client.post(f"/api/grns/{grn.id}/update-and-post/", {"remarks": "Anon update"})
    assert res.status_code == status.HTTP_403_FORBIDDEN
    
    res = unauth_client.patch(f"/api/delivery-notes/{dn.id}/", {"remarks": "Anon update"})
    assert res.status_code == status.HTTP_403_FORBIDDEN
    
    res = unauth_client.post(f"/api/delivery-notes/{dn.id}/update-and-post/", {"remarks": "Anon update"})
    assert res.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_update_and_post_delivery_note_api(auth_client, default_facility, party, commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 8, 7),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id
        }]
    )
    lot = grn.lots.first()
    
    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=party.id,
        dispatch_date=date(2026, 8, 8),
        status=DeliveryNote.Status.DRAFT,
        lines=[{
            "lot_id": lot.id,
            "qty": 30
        }]
    )
    
    payload = {
        "remarks": "Updated remarks through API",
        "lines": [{
            "lot_id": lot.id,
            "qty": 40
        }]
    }
    
    res = auth_client.post(f"/api/delivery-notes/{dn.id}/update-and-post/", payload, format="json")
    assert res.status_code == status.HTTP_200_OK
    
    dn.refresh_from_db()
    assert dn.status == DeliveryNote.Status.POSTED
    assert dn.remarks == "Updated remarks through API"
    assert dn.lines.first().qty == 40
    
    lot.refresh_from_db()
    assert lot.remaining_qty == 60

@pytest.mark.django_db
def test_update_and_post_delivery_note_api_rollback_on_post_failure(auth_client, default_facility, party, commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 8, 7),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id
        }]
    )
    lot = grn.lots.first()
    
    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=party.id,
        dispatch_date=date(2026, 8, 8),
        status=DeliveryNote.Status.DRAFT,
        remarks="Original remarks",
        lines=[{
            "lot_id": lot.id,
            "qty": 30
        }]
    )
    
    payload = {
        "remarks": "Attempted update remarks",
        "lines": [{
            "lot_id": lot.id,
            "qty": 150
        }]
    }
    
    res = auth_client.post(f"/api/delivery-notes/{dn.id}/update-and-post/", payload, format="json")
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    
    dn.refresh_from_db()
    assert dn.status == DeliveryNote.Status.DRAFT
    assert dn.remarks == "Original remarks"
    assert dn.lines.first().qty == 30
    
    lot.refresh_from_db()
    assert lot.remaining_qty == 100
