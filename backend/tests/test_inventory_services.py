import pytest
from datetime import date
from django.core.exceptions import ValidationError
from apps.parties.services import create_party
from apps.inventory.services import (
    create_commodity,
    update_commodity,
    create_grn,
    withdraw_stock_from_lot,
    post_grn,
    cancel_grn
)
from apps.inventory.selectors import get_lots_list
from apps.inventory.models import GRN, Lot

@pytest.fixture
def test_party(default_facility):
    return create_party(
        facility_id=default_facility.id,
        name="Test Farmer",
        code="FARM-01",
        type="DEPOSITOR"
    )

@pytest.fixture
def test_commodity(default_facility):
    return create_commodity(
        facility_id=default_facility.id,
        name="Cold Potato",
        code="POT-01",
        unit="BAGS"
    )

@pytest.mark.django_db
def test_create_commodity_success(default_facility):
    commodity = create_commodity(
        facility_id=default_facility.id,
        name="Royal Apple",
        code="APP-01",
        unit="BOXES",
        description="Fresh apples"
    )
    assert commodity.name == "Royal Apple"
    assert commodity.code == "APP-01"
    assert commodity.unit == "BOXES"
    assert commodity.facility == default_facility
    assert commodity.is_active is True
    assert commodity.history.count() == 1

@pytest.mark.django_db
def test_create_grn_with_sequence_and_lots(default_facility, test_party, test_commodity):
    receipt_date = date(2026, 7, 25)
    items = [
        {
            "commodity_id": test_commodity.id,
            "chamber": "Chamber A",
            "floor": "Floor 1",
            "rack": "Rack 05",
            "initial_qty": 100,
            "unit_weight": 50.0,
            "rent_rate_per_unit": 12.50
        },
        {
            "commodity_id": test_commodity.id,
            "chamber": "Chamber B",
            "floor": "Floor 2",
            "rack": "Rack 12",
            "initial_qty": 50,
            "unit_weight": 50.0,
            "rent_rate_per_unit": 12.50
        }
    ]

    grn1 = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=receipt_date,
        vehicle_number="KA-01-AB-1234",
        driver_name="Ramesh",
        items=items
    )

    assert grn1.grn_number == "GRN-000001"
    assert grn1.party == test_party
    assert grn1.status == GRN.Status.POSTED
    assert grn1.lots.count() == 2

    lots = list(grn1.lots.order_by('id'))
    assert lots[0].initial_qty == 100
    assert lots[0].remaining_qty == 100
    assert lots[0].lot_number == "LOT-000001"
    assert lots[0].chamber == "Chamber A"

    assert lots[1].initial_qty == 50
    assert lots[1].remaining_qty == 50
    assert lots[1].lot_number == "LOT-000002"

    # Create a second GRN to verify sequence auto-increments to GRN-000002
    grn2 = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=receipt_date,
        items=items
    )
    assert grn2.grn_number == "GRN-000002"

@pytest.mark.django_db
def test_withdraw_stock_from_lot_success(default_facility, test_party, test_commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 200,
            "unit_weight": 50.0
        }]
    )

    lot = grn.lots.first()
    assert lot.remaining_qty == 200

    # Withdraw 75 units
    updated_lot = withdraw_stock_from_lot(lot_id=lot.id, qty_to_withdraw=75)
    assert updated_lot.remaining_qty == 125

    # Withdraw another 25 units
    updated_lot_2 = withdraw_stock_from_lot(lot_id=lot.id, qty_to_withdraw=25)
    assert updated_lot_2.remaining_qty == 100

@pytest.mark.django_db
def test_withdraw_stock_from_lot_insufficient_stock(default_facility, test_party, test_commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 50
        }]
    )

    lot = grn.lots.first()

    with pytest.raises(ValidationError) as exc:
        withdraw_stock_from_lot(lot_id=lot.id, qty_to_withdraw=100)
    assert "Insufficient stock" in str(exc.value)


@pytest.mark.django_db
def test_post_grn_transitions_draft_to_posted(default_facility, test_party, test_commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.DRAFT,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100
        }]
    )
    assert grn.status == GRN.Status.DRAFT

    posted_grn = post_grn(grn_id=grn.id)
    assert posted_grn.status == GRN.Status.POSTED
    grn.refresh_from_db()
    assert grn.status == GRN.Status.POSTED


@pytest.mark.django_db
def test_post_grn_rejects_non_draft(default_facility, test_party, test_commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100
        }]
    )
    with pytest.raises(ValidationError) as exc:
        post_grn(grn_id=grn.id)
    assert "must be DRAFT" in str(exc.value)


@pytest.mark.django_db
def test_cancel_grn_from_draft(default_facility, test_party, test_commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.DRAFT,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100
        }]
    )
    cancelled_grn = cancel_grn(grn_id=grn.id)
    assert cancelled_grn.status == GRN.Status.CANCELLED
    grn.refresh_from_db()
    assert grn.status == GRN.Status.CANCELLED


@pytest.mark.django_db
def test_cancel_grn_rejects_posted(default_facility, test_party, test_commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100
        }]
    )
    with pytest.raises(ValidationError) as exc:
        cancel_grn(grn_id=grn.id)
    assert "must be DRAFT" in str(exc.value)


@pytest.mark.django_db
def test_withdraw_rejected_when_grn_is_draft(default_facility, test_party, test_commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.DRAFT,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100
        }]
    )
    lot = grn.lots.first()
    with pytest.raises(ValidationError) as exc:
        withdraw_stock_from_lot(lot_id=lot.id, qty_to_withdraw=20)
    assert "must be POSTED" in str(exc.value)

    lot.refresh_from_db()
    assert lot.remaining_qty == 100


@pytest.mark.django_db
def test_withdraw_succeeds_after_posting(default_facility, test_party, test_commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.DRAFT,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100
        }]
    )
    lot = grn.lots.first()

    post_grn(grn_id=grn.id)

    updated_lot = withdraw_stock_from_lot(lot_id=lot.id, qty_to_withdraw=30)
    assert updated_lot.remaining_qty == 70
    lot.refresh_from_db()
    assert lot.remaining_qty == 70


@pytest.mark.django_db
def test_get_lots_list_excludes_draft_grn_lots(default_facility, test_party, test_commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.DRAFT,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100
        }]
    )
    lot = grn.lots.first()

    lots = get_lots_list(facility_id=default_facility.id)
    assert lot not in lots

    post_grn(grn_id=grn.id)

    lots_after_post = get_lots_list(facility_id=default_facility.id)
    assert lot in lots_after_post


@pytest.mark.django_db
def test_grn_computed_loading_charge_flat_mode(default_facility, test_party, test_commodity):
    from decimal import Decimal
    from libs.choices import ChargeMode

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        loading_charge=Decimal('1500.00'),
        loading_charge_mode=ChargeMode.FLAT,
        items=[
            {"commodity_id": test_commodity.id, "initial_qty": 100},
            {"commodity_id": test_commodity.id, "initial_qty": 50},
            {"commodity_id": test_commodity.id, "initial_qty": 25}
        ]
    )
    assert grn.computed_loading_charge() == Decimal('1500.00')


@pytest.mark.django_db
def test_grn_computed_loading_charge_per_unit_mode(default_facility, test_party, test_commodity):
    from decimal import Decimal
    from libs.choices import ChargeMode

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        loading_unloading_rate_per_bag=Decimal('15.00'),
        loading_charge_mode=ChargeMode.PER_UNIT,
        items=[
            {"commodity_id": test_commodity.id, "initial_qty": 100},
            {"commodity_id": test_commodity.id, "initial_qty": 50},
            {"commodity_id": test_commodity.id, "initial_qty": 25}
        ]
    )
    # 175 units * 15.00 = 2625.00
    assert grn.computed_loading_charge() == Decimal('2625.00')


@pytest.mark.django_db
def test_lot_unit_override_and_fallback(default_facility, test_party, test_commodity):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        items=[
            {"commodity_id": test_commodity.id, "initial_qty": 100, "unit": "BOXES"},
            {"commodity_id": test_commodity.id, "initial_qty": 50}  # Omitted -> falls back to commodity.unit ('BAGS')
        ]
    )
    lots = list(grn.lots.order_by('id'))
    assert lots[0].unit == "BOXES"
    assert lots[1].unit == test_commodity.unit  # "BAGS"

