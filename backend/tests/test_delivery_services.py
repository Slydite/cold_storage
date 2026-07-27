import pytest
from datetime import date
from django.core.exceptions import ValidationError
from apps.parties.services import create_party
from apps.inventory.services import create_commodity, create_grn
from apps.delivery.services import (
    create_delivery_note,
    post_delivery_note,
    cancel_delivery_note
)
from apps.delivery.models import DeliveryNote
from apps.facilities.models import Facility


@pytest.fixture
def test_party(default_facility):
    return create_party(
        facility_id=default_facility.id,
        name="Test Customer",
        type="DEPOSITOR"
    )


@pytest.fixture
def test_commodity(default_facility):
    return create_commodity(
        facility_id=default_facility.id,
        name="Frozen Peas",
        unit="BAGS"
    )


@pytest.fixture
def posted_grn(default_facility, test_party, test_commodity):
    return create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        items=[
            {
                "commodity_id": test_commodity.id,
                "chamber": "Chamber A",
                "initial_qty": 100,
                "unit_weight": 50.0
            },
            {
                "commodity_id": test_commodity.id,
                "chamber": "Chamber B",
                "initial_qty": 200,
                "unit_weight": 50.0
            }
        ]
    )


@pytest.mark.django_db
def test_create_delivery_note_draft_does_not_change_stock(default_facility, test_party, posted_grn):
    lots = list(posted_grn.lots.order_by('id'))
    lot1, lot2 = lots[0], lots[1]

    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 25),
        vehicle_number="KA-01-DN-9999",
        driver_name="Ramu",
        remarks="Draft DN test",
        status=DeliveryNote.Status.DRAFT,
        lines=[
            {"lot_id": lot1.id, "qty": 40},
            {"lot_id": lot2.id, "qty": 50}
        ]
    )

    assert dn.dn_number == "DN-000001"
    assert dn.status == DeliveryNote.Status.DRAFT
    assert dn.lines.count() == 2

    # Stock quantity must remain completely unchanged for DRAFT
    lot1.refresh_from_db()
    lot2.refresh_from_db()
    assert lot1.remaining_qty == 100
    assert lot2.remaining_qty == 200


@pytest.mark.django_db
def test_post_delivery_note_withdraws_correct_qty(default_facility, test_party, posted_grn):
    lot = posted_grn.lots.first()
    assert lot.remaining_qty == 100

    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 25),
        status=DeliveryNote.Status.DRAFT,
        lines=[{"lot_id": lot.id, "qty": 35}]
    )

    posted_dn = post_delivery_note(delivery_note_id=dn.id)
    assert posted_dn.status == DeliveryNote.Status.POSTED

    lot.refresh_from_db()
    assert lot.remaining_qty == 65


@pytest.mark.django_db
def test_post_delivery_note_insufficient_stock_rolls_back_transaction(default_facility, test_party, posted_grn):
    lots = list(posted_grn.lots.order_by('id'))
    lot1, lot2 = lots[0], lots[1]  # lot1: 100, lot2: 200

    # Line 1 is valid (30 <= 100), Line 2 exceeds stock (250 > 200)
    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 25),
        status=DeliveryNote.Status.DRAFT,
        lines=[
            {"lot_id": lot1.id, "qty": 30},
            {"lot_id": lot2.id, "qty": 250}
        ]
    )

    with pytest.raises(ValidationError) as exc:
        post_delivery_note(delivery_note_id=dn.id)

    assert "Insufficient stock" in str(exc.value)

    # Verify transaction rollback — BOTH lots remain completely unchanged
    lot1.refresh_from_db()
    lot2.refresh_from_db()
    assert lot1.remaining_qty == 100
    assert lot2.remaining_qty == 200

    # DN status remains DRAFT
    dn.refresh_from_db()
    assert dn.status == DeliveryNote.Status.DRAFT


@pytest.mark.django_db
def test_multiline_dn_across_two_lots(default_facility, test_party, posted_grn):
    lots = list(posted_grn.lots.order_by('id'))
    lot1, lot2 = lots[0], lots[1]

    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 25),
        status=DeliveryNote.Status.DRAFT,
        lines=[
            {"lot_id": lot1.id, "qty": 30},
            {"lot_id": lot2.id, "qty": 70}
        ]
    )

    post_delivery_note(delivery_note_id=dn.id)

    lot1.refresh_from_db()
    lot2.refresh_from_db()
    assert lot1.remaining_qty == 70
    assert lot2.remaining_qty == 130


@pytest.mark.django_db
def test_post_already_posted_dn_raises_validation_error(default_facility, test_party, posted_grn):
    lot = posted_grn.lots.first()
    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 25),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 20}]
    )
    assert dn.status == DeliveryNote.Status.POSTED

    with pytest.raises(ValidationError) as exc:
        post_delivery_note(delivery_note_id=dn.id)
    assert "must be DRAFT" in str(exc.value)


@pytest.mark.django_db
def test_cancel_delivery_note_lifecycle(default_facility, test_party, posted_grn):
    lot = posted_grn.lots.first()
    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 25),
        status=DeliveryNote.Status.DRAFT,
        lines=[{"lot_id": lot.id, "qty": 20}]
    )

    cancelled_dn = cancel_delivery_note(delivery_note_id=dn.id)
    assert cancelled_dn.status == DeliveryNote.Status.CANCELLED
    dn.refresh_from_db()
    assert dn.status == DeliveryNote.Status.CANCELLED

    # Cannot cancel an already posted DN
    posted_dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 25),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 10}]
    )
    with pytest.raises(ValidationError) as exc:
        cancel_delivery_note(delivery_note_id=posted_dn.id)
    assert "must be DRAFT" in str(exc.value)


@pytest.mark.django_db
def test_dn_number_sequence_and_increment(default_facility, test_party, posted_grn):
    lot = posted_grn.lots.first()
    dn1 = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 25),
        lines=[{"lot_id": lot.id, "qty": 5}]
    )
    dn2 = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 25),
        lines=[{"lot_id": lot.id, "qty": 5}]
    )

    assert dn1.dn_number == "DN-000001"
    assert dn2.dn_number == "DN-000002"


@pytest.mark.django_db
def test_create_delivery_note_facility_validation(default_facility, test_party, test_commodity):
    other_facility = Facility.objects.create(code="FAC-02", name="Other Facility")
    grn_other = create_grn(
        facility_id=other_facility.id,
        party_id=create_party(facility_id=other_facility.id, name="Other Party", type="DEPOSITOR").id,
        receipt_date=date(2026, 7, 25),
        items=[{"commodity_id": create_commodity(facility_id=other_facility.id, name="Peas 2").id, "initial_qty": 50}]
    )
    other_lot = grn_other.lots.first()

    with pytest.raises(ValidationError) as exc:
        create_delivery_note(
            facility_id=default_facility.id,
            party_id=test_party.id,
            dispatch_date=date(2026, 7, 25),
            lines=[{"lot_id": other_lot.id, "qty": 10}]
        )
    assert "does not exist in facility" in str(exc.value)


@pytest.mark.django_db
def test_dn_computed_loading_charge_flat_mode(default_facility, test_party, posted_grn):
    from decimal import Decimal
    from libs.choices import ChargeMode

    lots = list(posted_grn.lots.order_by('id'))
    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 25),
        loading_charge=Decimal('800.00'),
        loading_charge_mode=ChargeMode.FLAT,
        lines=[
            {"lot_id": lots[0].id, "qty": 40},
            {"lot_id": lots[1].id, "qty": 80}
        ]
    )
    assert dn.computed_loading_charge() == Decimal('800.00')


@pytest.mark.django_db
def test_dn_computed_loading_charge_per_unit_mode(default_facility, test_party, posted_grn):
    from decimal import Decimal
    from libs.choices import ChargeMode

    lots = list(posted_grn.lots.order_by('id'))
    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 7, 25),
        loading_unloading_rate_per_unit=Decimal('5.50'),
        loading_charge_mode=ChargeMode.PER_UNIT,
        lines=[
            {"lot_id": lots[0].id, "qty": 40},
            {"lot_id": lots[1].id, "qty": 60}
        ]
    )
    # 100 units * 5.50 = 550.00
    assert dn.computed_loading_charge() == Decimal('550.00')
