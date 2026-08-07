import pytest
from decimal import Decimal
from rest_framework import status
from datetime import date
from apps.parties.services import create_party
from apps.inventory.services import create_commodity, create_grn

@pytest.fixture
def party(default_facility):
    return create_party(facility_id=default_facility.id, name="API Farmer", type="DEPOSITOR")

@pytest.fixture
def commodity(default_facility):
    return create_commodity(facility_id=default_facility.id, name="Onion", unit="BAGS")

@pytest.mark.django_db
def test_unauthenticated_inventory_denied(api_client):
    assert api_client.get('/api/commodities/').status_code == status.HTTP_403_FORBIDDEN
    assert api_client.get('/api/grns/').status_code == status.HTTP_403_FORBIDDEN
    assert api_client.get('/api/lots/').status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_commodity_api_lifecycle(auth_client, default_facility):
    # Create commodity (client-supplied code is ignored)
    data = {
        "facility_id": default_facility.id,
        "name": "Carrot",
        "code": "CLIENT-CODE-IGNORED",
        "unit": "BAGS",
        "description": "Orange carrots"
    }
    res = auth_client.post('/api/commodities/', data)
    assert res.status_code == status.HTTP_201_CREATED
    comm_id = res.data['id']
    assert res.data['name'] == "Carrot"
    assert res.data['code'] == "CMD-000001"

    # List commodities
    res_list = auth_client.get(f'/api/commodities/?facility_id={default_facility.id}')
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.data) == 1

    # Update commodity
    update_data = {
        "facility_id": default_facility.id,
        "name": "Red Carrot",
        "unit": "BAGS",
        "is_active": True
    }
    res_upd = auth_client.put(f'/api/commodities/{comm_id}/', update_data)
    assert res_upd.status_code == status.HTTP_200_OK
    assert res_upd.data['name'] == "Red Carrot"
    assert res_upd.data['code'] == "CMD-000001"

@pytest.mark.django_db
def test_grn_api_create_and_list(auth_client, default_facility, party, commodity):
    from apps.locations.services import create_chamber, create_floor, create_block
    chamber = create_chamber(facility_id=default_facility.id, name="Chamber 1")
    floor = create_floor(chamber_id=chamber.id, name="Floor 1")
    block = create_block(floor_id=floor.id, name="Block 1")

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
                "rent_rate_per_unit": "10.00",
                "block_id": block.id
            }
        ]
    }

    res = auth_client.post('/api/grns/', grn_payload, format='json')
    assert res.status_code == status.HTTP_201_CREATED
    assert res.data['grn_number'] == "20260725-01069"
    assert res.data['party_name'] == "Api Farmer"
    assert len(res.data['lots']) == 1
    assert res.data['lots'][0]['remaining_qty'] == 300

    # List GRNs
    res_list = auth_client.get(f'/api/grns/?facility_id={default_facility.id}')
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.data) == 1

@pytest.mark.django_db
def test_lot_api_withdraw(auth_client, default_facility, party, commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 25),
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 500,
            "chamber": "Chamber 3",
            "block_id": default_block.id,
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


@pytest.mark.django_db
def test_grn_api_roundtrip_loading_charge_mode(auth_client, default_facility, party, commodity):
    from apps.locations.services import create_chamber, create_floor, create_block
    chamber = create_chamber(facility_id=default_facility.id, name="Chamber 1")
    floor = create_floor(chamber_id=chamber.id, name="Floor 1")
    block = create_block(floor_id=floor.id, name="Block 1")

    grn_payload = {
        "facility_id": default_facility.id,
        "party_id": party.id,
        "receipt_date": "2026-07-25",
        "loading_charge_mode": "PER_UNIT",
        "loading_unloading_rate_per_bag": "12.50",
        "items": [
            {
                "commodity_id": commodity.id,
                "initial_qty": 200,
                "unit": "CRATES",
                "block_id": block.id
            }
        ]
    }

    res = auth_client.post('/api/grns/', grn_payload, format='json')
    assert res.status_code == status.HTTP_201_CREATED
    assert res.data['loading_charge_mode'] == "PER_UNIT"
    assert res.data['computed_loading_charge'] == Decimal("2500.00")
    assert res.data['lots'][0]['unit'] == "CRATES"


@pytest.mark.django_db
def test_reserve_number_returns_404(auth_client, default_facility):
    res = auth_client.post('/api/lots/reserve-number/', {"facility_id": default_facility.id})
    assert res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_grn_created_with_ignored_lot_number(auth_client, default_facility, party, commodity):
    from apps.locations.services import create_chamber, create_floor, create_block
    from libs.lot_numbers import is_valid_lot_number
    chamber = create_chamber(facility_id=default_facility.id, name="Chamber 1")
    floor = create_floor(chamber_id=chamber.id, name="Floor 1")
    block = create_block(floor_id=floor.id, name="Block 1")

    grn_payload = {
        "facility_id": default_facility.id,
        "party_id": party.id,
        "receipt_date": "2026-07-25",
        "items": [
            {
                "commodity_id": commodity.id,
                "initial_qty": 300,
                "lot_number": "LOT-123456",
                "block_id": block.id
            }
        ]
    }
    res_grn = auth_client.post('/api/grns/', grn_payload, format='json')
    assert res_grn.status_code == status.HTTP_201_CREATED
    created_lot_number = res_grn.data['lots'][0]['lot_number']
    assert created_lot_number != "LOT-123456"
    assert is_valid_lot_number(created_lot_number)


@pytest.mark.django_db
def test_grn_email_api_workflow(auth_client, default_facility, party, commodity):
    # Unauthenticated access is covered separately by
    # test_grn_email_action_genuinely_unauthenticated: requesting both
    # auth_client and api_client in one test resolves to the SAME already-
    # authenticated instance (auth_client's own fixture depends on api_client),
    # so an "unauthenticated" assertion here would silently pass for the
    # wrong reason.
    from django.core import mail
    from django.utils import timezone
    from apps.parties.models import Party
    from apps.locations.services import create_chamber, create_floor, create_block

    chamber = create_chamber(facility_id=default_facility.id, name="Chamber 1")
    floor = create_floor(chamber_id=chamber.id, name="Floor 1")
    block = create_block(floor_id=floor.id, name="Block 1")

    # Create GRN
    grn_payload = {
        "facility_id": default_facility.id,
        "party_id": party.id,
        "receipt_date": "2026-07-25",
        "items": [
            {
                "commodity_id": commodity.id,
                "initial_qty": 100,
                "block_id": block.id
            }
        ]
    }
    res_create = auth_client.post('/api/grns/', grn_payload, format='json')
    assert res_create.status_code == status.HTTP_201_CREATED
    grn_id = res_create.data['id']
    assert res_create.data['last_emailed_at'] is None

    # 2. Party has blank email by default -> 400 ValidationError, does not send
    mail.outbox.clear()
    res_email_blank = auth_client.post(f'/api/grns/{grn_id}/email/')
    assert res_email_blank.status_code == status.HTTP_400_BAD_REQUEST
    assert "does not have an email address on file" in res_email_blank.data['detail']
    assert len(mail.outbox) == 0

    # 3. Update party to have email
    p_obj = Party.objects.get(pk=party.id)
    p_obj.email = "depositor@example.com"
    p_obj.save()

    # 4. Email GRN -> 200, sends mail, updates last_emailed_at
    mail.outbox.clear()
    res_email_success = auth_client.post(f'/api/grns/{grn_id}/email/')
    assert res_email_success.status_code == status.HTTP_200_OK
    assert res_email_success.data['last_emailed_at'] is not None

    # Check email sent
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.to == ["depositor@example.com"]
    assert "GRN" in msg.subject
    assert len(msg.attachments) == 1
    filename, content, mimetype = msg.attachments[0]
    assert filename.endswith('.pdf')
    assert mimetype == 'application/pdf'
    assert content.startswith(b'%PDF')



@pytest.mark.django_db
def test_grn_email_action_genuinely_unauthenticated():
    """See test_invoice_email_action_genuinely_unauthenticated for why this
    must be a standalone client rather than reusing api_client alongside
    auth_client in the same test."""
    from rest_framework.test import APIClient
    fresh_client = APIClient()
    res = fresh_client.post('/api/grns/999/email/')
    assert res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_create_grn_block_required_api(auth_client, default_facility, party, commodity):
    # Test that creating a GRN without a block_id is rejected with a 400 and names the commodity
    payload = {
        "facility_id": default_facility.id,
        "party_id": party.id,
        "receipt_date": "2026-07-25",
        "items": [
            {
                "commodity_id": commodity.id,
                "initial_qty": 100,
                # block_id is missing!
            }
        ]
    }
    res = auth_client.post('/api/grns/', payload, format='json')
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "Onion" in str(res.data)
    assert "block" in str(res.data) or "location" in str(res.data)


@pytest.mark.django_db
def test_create_grn_valid_block_api(auth_client, default_facility, party, commodity):
    from apps.locations.services import create_chamber, create_floor, create_block
    from apps.inventory.models import Lot
    chamber = create_chamber(facility_id=default_facility.id, name="Chamber X")
    floor = create_floor(chamber_id=chamber.id, name="Floor Y")
    block = create_block(floor_id=floor.id, name="Block Z")

    payload = {
        "facility_id": default_facility.id,
        "party_id": party.id,
        "receipt_date": "2026-07-25",
        "items": [
            {
                "commodity_id": commodity.id,
                "initial_qty": 100,
                "block_id": block.id
            }
        ]
    }
    res = auth_client.post('/api/grns/', payload, format='json')
    assert res.status_code == status.HTTP_201_CREATED
    lot = Lot.objects.get(pk=res.data['lots'][0]['id'])
    assert lot.block_ref_id == block.id
    assert lot.floor_ref_id == floor.id
    assert lot.chamber_ref_id == chamber.id


@pytest.mark.django_db
def test_create_grn_mismatched_locations_rejected(auth_client, default_facility, party, commodity):
    from apps.locations.services import create_chamber, create_floor, create_block
    chamber1 = create_chamber(facility_id=default_facility.id, name="Chamber 1")
    floor1 = create_floor(chamber_id=chamber1.id, name="Floor 1")
    block1 = create_block(floor_id=floor1.id, name="Block 1")

    chamber2 = create_chamber(facility_id=default_facility.id, name="Chamber 2")

    payload = {
        "facility_id": default_facility.id,
        "party_id": party.id,
        "receipt_date": "2026-07-25",
        "items": [
            {
                "commodity_id": commodity.id,
                "initial_qty": 100,
                "block_id": block1.id,
                "chamber_id": chamber2.id  # Mismatched chamber!
            }
        ]
    }
    res = auth_client.post('/api/grns/', payload, format='json')
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "does not belong to chamber" in str(res.data)


@pytest.mark.django_db
def test_adjust_lot_stock_api_auth_required(default_facility, party, commodity, default_block):
    from rest_framework.test import APIClient
    from rest_framework import status
    from apps.inventory.services import create_grn
    from apps.inventory.models import GRN
    from datetime import date

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    unauth_client = APIClient()
    res = unauth_client.post(
        f'/api/lots/{lot.id}/adjust/',
        {'qty_delta': -10, 'reason': 'SPOILAGE'},
        format='json'
    )
    assert res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_adjust_lot_stock_api_success_and_failures(auth_client, default_facility, party, commodity, default_block):
    from rest_framework import status
    from apps.inventory.services import create_grn
    from apps.inventory.models import GRN
    from datetime import date

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    # Success: Reduce stock
    payload = {
        'qty_delta': -30,
        'reason': 'SPOILAGE',
        'note': 'Some spoiled potatoes'
    }
    res = auth_client.post(f'/api/lots/{lot.id}/adjust/', payload, format='json')
    assert res.status_code == status.HTTP_200_OK
    assert res.data['remaining_qty'] == 70
    assert len(res.data['adjustments']) == 1
    assert res.data['adjustments'][0]['qty_delta'] == -30
    assert res.data['adjustments'][0]['reason'] == 'SPOILAGE'

    # Failure: Adjust resulting in negative qty
    payload_neg = {
        'qty_delta': -80,
        'reason': 'NOT_FOUND'
    }
    res_neg = auth_client.post(f'/api/lots/{lot.id}/adjust/', payload_neg, format='json')
    assert res_neg.status_code == status.HTTP_400_BAD_REQUEST
    assert 'resulting quantity may not be negative' in res_neg.data['detail']


@pytest.mark.django_db
def test_commodity_alias_and_merge_api(auth_client, default_facility):
    from rest_framework import status
    from rest_framework.test import APIClient
    from apps.inventory.services import create_commodity
    from apps.inventory.models import Commodity, CommodityAlias

    c1 = create_commodity(facility_id=default_facility.id, name="Jeera", unit="BAGS")
    c2 = create_commodity(facility_id=default_facility.id, name="Cumin", unit="BAGS")

    # 1. API Endpoints require authentication (using a fresh APIClient)
    anon_client = APIClient()

    # POST /api/commodities/{id}/aliases/
    res_anon_add = anon_client.post(f'/api/commodities/{c1.id}/aliases/', {'name': 'Jira'})
    assert res_anon_add.status_code == status.HTTP_403_FORBIDDEN

    # DELETE /api/commodities/{id}/aliases/{alias_id}/
    res_anon_del = anon_client.delete(f'/api/commodities/{c1.id}/aliases/999/')
    assert res_anon_del.status_code == status.HTTP_403_FORBIDDEN

    # POST /api/commodities/{id}/merge/
    res_anon_merge = anon_client.post(f'/api/commodities/{c1.id}/merge/', {'source_commodity_id': c2.id})
    assert res_anon_merge.status_code == status.HTTP_403_FORBIDDEN

    # 2. Add alias via API (authenticated)
    res_add = auth_client.post(f'/api/commodities/{c1.id}/aliases/', {'name': 'Jira'}, format='json')
    assert res_add.status_code == status.HTTP_201_CREATED
    alias_id = res_add.data['id']
    assert res_add.data['name'] == "Jira"

    # Check nested aliases list
    res_ret = auth_client.get(f'/api/commodities/{c1.id}/')
    assert res_ret.status_code == status.HTTP_200_OK
    assert len(res_ret.data['aliases']) == 1
    assert res_ret.data['aliases'][0]['name'] == "Jira"

    # 3. Search matches aliases
    res_search = auth_client.get(f'/api/commodities/?facility_id={default_facility.id}&search=Jira')
    assert res_search.status_code == status.HTTP_200_OK
    assert len(res_search.data) == 1
    assert res_search.data[0]['id'] == c1.id

    # 4. Remove alias via API
    res_del_wrong = auth_client.delete(f'/api/commodities/{c2.id}/aliases/{alias_id}/')
    assert res_del_wrong.status_code == status.HTTP_400_BAD_REQUEST
    assert "Alias does not belong to this commodity" in res_del_wrong.data['detail']

    res_del = auth_client.delete(f'/api/commodities/{c1.id}/aliases/{alias_id}/')
    assert res_del.status_code == status.HTTP_204_NO_CONTENT
    assert not CommodityAlias.objects.filter(id=alias_id).exists()

    # 5. Merge via API
    res_merge = auth_client.post(f'/api/commodities/{c1.id}/merge/', {'source_commodity_id': c2.id}, format='json')
    assert res_merge.status_code == status.HTTP_200_OK

    assert not Commodity.objects.filter(id=c2.id).exists()
    assert CommodityAlias.objects.filter(commodity=c1, name="Cumin").exists()


