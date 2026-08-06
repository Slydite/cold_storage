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
        type="DEPOSITOR"
    )

@pytest.fixture
def test_commodity(default_facility):
    return create_commodity(
        facility_id=default_facility.id,
        name="Cold Potato",
        unit="BAGS"
    )

@pytest.mark.django_db
def test_create_commodity_success(default_facility):
    commodity = create_commodity(
        facility_id=default_facility.id,
        name="Royal Apple",
        unit="BOXES",
        description="  Fresh   apples  "
    )
    assert commodity.name == "Royal Apple"
    assert commodity.code == "CMD-000001"
    assert commodity.unit == "BOXES"
    assert commodity.description == "Fresh apples"
    assert commodity.facility == default_facility
    assert commodity.is_active is True
    assert commodity.history.count() == 1

@pytest.mark.django_db
def test_create_commodity_sequence_advances(default_facility):
    c1 = create_commodity(facility_id=default_facility.id, name="Commodity 1")
    c2 = create_commodity(facility_id=default_facility.id, name="Commodity 2")
    assert c1.code == "CMD-000001"
    assert c2.code == "CMD-000002"
    assert c1.code != c2.code

@pytest.mark.django_db
def test_create_grn_with_sequence_and_lots(default_facility, test_party, test_commodity):
    from apps.locations.services import create_chamber, create_floor, create_block
    ch_a = create_chamber(facility_id=default_facility.id, name="Chamber A")
    fl_1 = create_floor(chamber_id=ch_a.id, name="Floor 1")
    bl_1 = create_block(floor_id=fl_1.id, name="Block 1")

    ch_b = create_chamber(facility_id=default_facility.id, name="Chamber B")
    fl_2 = create_floor(chamber_id=ch_b.id, name="Floor 2")
    bl_2 = create_block(floor_id=fl_2.id, name="Block 2")

    receipt_date = date(2026, 7, 25)
    items = [
        {
            "commodity_id": test_commodity.id,
            "chamber": "Chamber A",
            "floor": "Floor 1",
            "rack": "Rack 05",
            "initial_qty": 100,
            "unit_weight": 50.0,
            "rent_rate_per_unit": 12.50,
            "block_id": bl_1.id,
        },
        {
            "commodity_id": test_commodity.id,
            "chamber": "Chamber B",
            "floor": "Floor 2",
            "rack": "Rack 12",
            "initial_qty": 50,
            "unit_weight": 50.0,
            "rent_rate_per_unit": 12.50,
            "block_id": bl_2.id,
        }
    ]

    grn1 = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=receipt_date,
        vehicle_number="ka-01-ab-1234",
        driver_name=" ramesh ",
        items=items
    )

    assert grn1.grn_number == "20260725-01069"
    assert grn1.vehicle_number == "KA-01-AB-1234"
    assert grn1.driver_name == "Ramesh"
    assert grn1.party == test_party
    assert grn1.status == GRN.Status.POSTED
    assert grn1.lots.count() == 2

    lots = list(grn1.lots.order_by('id'))
    assert lots[0].initial_qty == 100
    assert lots[0].remaining_qty == 100
    assert lots[0].lot_number == "20260725-02607-00100"
    assert lots[0].chamber == "Chamber A"

    assert lots[1].initial_qty == 50
    assert lots[1].remaining_qty == 50
    assert lots[1].lot_number == "20260725-02608-00050"

    # Create a second GRN to verify sequence auto-increments to GRN-000002
    grn2 = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=receipt_date,
        items=items
    )
    assert grn2.grn_number == "20260725-01070"

@pytest.mark.django_db
def test_withdraw_stock_from_lot_success(default_facility, test_party, test_commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 200,
            "unit_weight": 50.0,
            "block_id": default_block.id,
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
def test_withdraw_stock_from_lot_insufficient_stock(default_facility, test_party, test_commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 50,
            "block_id": default_block.id,
        }]
    )

    lot = grn.lots.first()

    with pytest.raises(ValidationError) as exc:
        withdraw_stock_from_lot(lot_id=lot.id, qty_to_withdraw=100)
    assert "Insufficient stock" in str(exc.value)


@pytest.mark.django_db
def test_post_grn_transitions_draft_to_posted(default_facility, test_party, test_commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.DRAFT,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id,
        }]
    )
    assert grn.status == GRN.Status.DRAFT

    posted_grn = post_grn(grn_id=grn.id)
    assert posted_grn.status == GRN.Status.POSTED
    grn.refresh_from_db()
    assert grn.status == GRN.Status.POSTED


@pytest.mark.django_db
def test_post_grn_rejects_non_draft(default_facility, test_party, test_commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id,
        }]
    )
    with pytest.raises(ValidationError) as exc:
        post_grn(grn_id=grn.id)
    assert "must be DRAFT" in str(exc.value)


@pytest.mark.django_db
def test_cancel_grn_from_draft(default_facility, test_party, test_commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.DRAFT,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id,
        }]
    )
    cancelled_grn = cancel_grn(grn_id=grn.id)
    assert cancelled_grn.status == GRN.Status.CANCELLED
    grn.refresh_from_db()
    assert grn.status == GRN.Status.CANCELLED


@pytest.mark.django_db
def test_cancel_grn_rejects_posted(default_facility, test_party, test_commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id,
        }]
    )
    with pytest.raises(ValidationError) as exc:
        cancel_grn(grn_id=grn.id)
    assert "must be DRAFT" in str(exc.value)


@pytest.mark.django_db
def test_withdraw_rejected_when_grn_is_draft(default_facility, test_party, test_commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.DRAFT,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()
    with pytest.raises(ValidationError) as exc:
        withdraw_stock_from_lot(lot_id=lot.id, qty_to_withdraw=20)
    assert "must be POSTED" in str(exc.value)

    lot.refresh_from_db()
    assert lot.remaining_qty == 100


@pytest.mark.django_db
def test_withdraw_succeeds_after_posting(default_facility, test_party, test_commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.DRAFT,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    post_grn(grn_id=grn.id)

    updated_lot = withdraw_stock_from_lot(lot_id=lot.id, qty_to_withdraw=30)
    assert updated_lot.remaining_qty == 70
    lot.refresh_from_db()
    assert lot.remaining_qty == 70


@pytest.mark.django_db
def test_get_lots_list_excludes_draft_grn_lots(default_facility, test_party, test_commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.DRAFT,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    lots = get_lots_list(facility_id=default_facility.id)
    assert lot not in lots

    post_grn(grn_id=grn.id)

    lots_after_post = get_lots_list(facility_id=default_facility.id)
    assert lot in lots_after_post


@pytest.mark.django_db
def test_grn_computed_loading_charge_flat_mode(default_facility, test_party, test_commodity, default_block):
    from decimal import Decimal
    from libs.choices import ChargeMode

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        loading_charge=Decimal('1500.00'),
        loading_charge_mode=ChargeMode.FLAT,
        items=[
            {"commodity_id": test_commodity.id, "initial_qty": 100, "block_id": default_block.id},
            {"commodity_id": test_commodity.id, "initial_qty": 50, "block_id": default_block.id},
            {"commodity_id": test_commodity.id, "initial_qty": 25, "block_id": default_block.id}
        ]
    )
    assert grn.computed_loading_charge() == Decimal('1500.00')


@pytest.mark.django_db
def test_grn_computed_loading_charge_per_unit_mode(default_facility, test_party, test_commodity, default_block):
    from decimal import Decimal
    from libs.choices import ChargeMode

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        loading_unloading_rate_per_bag=Decimal('15.00'),
        loading_charge_mode=ChargeMode.PER_UNIT,
        items=[
            {"commodity_id": test_commodity.id, "initial_qty": 100, "block_id": default_block.id},
            {"commodity_id": test_commodity.id, "initial_qty": 50, "block_id": default_block.id},
            {"commodity_id": test_commodity.id, "initial_qty": 25, "block_id": default_block.id}
        ]
    )
    # 175 units * 15.00 = 2625.00
    assert grn.computed_loading_charge() == Decimal('2625.00')


@pytest.mark.django_db
def test_lot_unit_override_and_fallback(default_facility, test_party, test_commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        items=[
            {"commodity_id": test_commodity.id, "initial_qty": 100, "unit": "BOXES", "block_id": default_block.id},
            {"commodity_id": test_commodity.id, "initial_qty": 50, "block_id": default_block.id}  # Omitted -> falls back to commodity.unit ('BAGS')
        ]
    )
    lots = list(grn.lots.order_by('id'))
    assert lots[0].unit == "BOXES"
    assert lots[1].unit == test_commodity.unit  # "BAGS"


@pytest.mark.django_db
def test_duplicate_lot_number_same_facility_fails(default_facility, test_party, test_commodity, default_block):
    from django.db import IntegrityError
    create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "lot_number": "LOT-000001",
            "block_id": default_block.id,
        }]
    )
    with pytest.raises((ValidationError, IntegrityError)):
        create_grn(
            facility_id=default_facility.id,
            party_id=test_party.id,
            receipt_date=date(2026, 7, 25),
            items=[{
                "commodity_id": test_commodity.id,
                "initial_qty": 100,
                "lot_number": "LOT-000001",
                "block_id": default_block.id,
            }]
        )


@pytest.mark.django_db
def test_same_lot_number_different_facility_allowed(default_facility, test_party, test_commodity, default_block):
    from apps.facilities.models import Facility
    from apps.locations.services import create_chamber, create_floor, create_block
    other_facility = Facility.objects.create(
        code="FAC-02",
        name="Second Facility",
        address="456 Cold Road"
    )
    other_party = create_party(facility_id=other_facility.id, name="Other Farmer", type="DEPOSITOR")
    other_commodity = create_commodity(facility_id=other_facility.id, name="Apple", unit="BAGS")
    other_chamber = create_chamber(facility_id=other_facility.id, name="Other Chamber")
    other_floor = create_floor(chamber_id=other_chamber.id, name="Other Floor")
    other_block = create_block(floor_id=other_floor.id, name="Other Block")

    create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "lot_number": "LOT-000001",
            "block_id": default_block.id,
        }]
    )

    grn_other = create_grn(
        facility_id=other_facility.id,
        party_id=other_party.id,
        receipt_date=date(2026, 7, 25),
        items=[{
            "commodity_id": other_commodity.id,
            "initial_qty": 100,
            "lot_number": "LOT-000001",
            "block_id": other_block.id,
        }]
    )
    assert grn_other.lots.first().lot_number == "LOT-000001"


@pytest.mark.django_db
def test_client_supplied_lot_number_bogus_format_rejected(default_facility, test_party, test_commodity, default_block):
    for bogus_lot in ["HACKED", "LOT-abc", ""]:
        if bogus_lot == "":
            grn = create_grn(
                facility_id=default_facility.id,
                party_id=test_party.id,
                receipt_date=date(2026, 7, 25),
                items=[{
                    "commodity_id": test_commodity.id,
                    "initial_qty": 100,
                    "lot_number": bogus_lot,
                    "block_id": default_block.id,
                }]
            )
            lot_num = grn.lots.first().lot_number
            assert len(lot_num) == 20 and lot_num[8] == '-' and lot_num[14] == '-'
        else:
            with pytest.raises(ValidationError) as exc:
                create_grn(
                    facility_id=default_facility.id,
                    party_id=test_party.id,
                    receipt_date=date(2026, 7, 25),
                    items=[{
                        "commodity_id": test_commodity.id,
                        "initial_qty": 100,
                        "lot_number": bogus_lot,
                        "block_id": default_block.id,
                    }]
                )
            assert "Invalid lot number format" in str(exc.value)


@pytest.mark.django_db
def test_omitting_lot_number_auto_generates(default_facility, test_party, test_commodity, default_block):
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id,
        }]
    )
    assert grn.lots.first().lot_number == "20260725-02607-00100"


@pytest.mark.django_db
def test_adjust_lot_stock_success(default_facility, test_party, test_commodity, default_block):
    from apps.inventory.services import adjust_lot_stock
    from apps.inventory.models import StockAdjustment
    from apps.delivery.models import DeliveryNote, DeliveryLine
    from apps.invoicing.models import Invoice

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    # Capture counts before adjustment
    dn_count = DeliveryNote.objects.count()
    dl_count = DeliveryLine.objects.count()
    inv_count = Invoice.objects.count()

    # 1. Reducing stock (delta = -20)
    adjustment = adjust_lot_stock(
        lot_id=lot.id,
        qty_delta=-20,
        reason=StockAdjustment.Reason.SPOILAGE,
        adjustment_date=date(2026, 7, 26),
        note="Spoiled apples",
        adjusted_by=None
    )

    lot.refresh_from_db()
    assert lot.remaining_qty == 80
    assert adjustment.qty_delta == -20
    assert adjustment.qty_before == 100
    assert adjustment.qty_after == 80
    assert adjustment.reason == StockAdjustment.Reason.SPOILAGE
    assert adjustment.note == "Spoiled apples"
    assert adjustment.adjustment_date == date(2026, 7, 26)

    # 2. Increasing stock (new_qty = 95, delta should be +15)
    adjustment_up = adjust_lot_stock(
        lot_id=lot.id,
        new_qty=95,
        reason=StockAdjustment.Reason.FOUND_EXTRA,
        adjustment_date=date(2026, 7, 27),
        note="Found extra bags during recount",
        adjusted_by=None
    )

    lot.refresh_from_db()
    assert lot.remaining_qty == 95
    assert adjustment_up.qty_delta == 15
    assert adjustment_up.qty_before == 80
    assert adjustment_up.qty_after == 95
    assert adjustment_up.reason == StockAdjustment.Reason.FOUND_EXTRA

    # Assert no delivery note or invoice was created
    assert DeliveryNote.objects.count() == dn_count
    assert DeliveryLine.objects.count() == dl_count
    assert Invoice.objects.count() == inv_count


@pytest.mark.django_db
def test_adjust_lot_stock_validation_failures(default_facility, test_party, test_commodity, default_block):
    from apps.inventory.services import adjust_lot_stock
    from apps.inventory.models import StockAdjustment

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 50,
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    # Zero net change rejected
    with pytest.raises(ValidationError) as exc:
        adjust_lot_stock(
            lot_id=lot.id,
            qty_delta=0,
            reason=StockAdjustment.Reason.COUNT_CORRECTION,
            adjustment_date=date(2026, 7, 26)
        )
    assert "zero net change" in str(exc.value)

    # Resulting negative quantity rejected
    with pytest.raises(ValidationError) as exc:
        adjust_lot_stock(
            lot_id=lot.id,
            qty_delta=-60,
            reason=StockAdjustment.Reason.NOT_FOUND,
            adjustment_date=date(2026, 7, 26)
        )
    assert "resulting quantity may not be negative" in str(exc.value)
    assert lot.lot_number in str(exc.value)

    # OTHER reason without a note is rejected
    with pytest.raises(ValidationError) as exc:
        adjust_lot_stock(
            lot_id=lot.id,
            qty_delta=10,
            reason=StockAdjustment.Reason.OTHER,
            adjustment_date=date(2026, 7, 26),
            note=""
        )
    assert "Note is mandatory when reason is OTHER" in str(exc.value)

    # DRAFT GRN adjustment is rejected
    draft_grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 25),
        status=GRN.Status.DRAFT,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 50,
            "block_id": default_block.id,
        }]
    )
    draft_lot = draft_grn.lots.first()
    with pytest.raises(ValidationError) as exc:
        adjust_lot_stock(
            lot_id=draft_lot.id,
            qty_delta=10,
            reason=StockAdjustment.Reason.COUNT_CORRECTION,
            adjustment_date=date(2026, 7, 26)
        )
    assert "must be POSTED" in str(exc.value)


@pytest.mark.django_db
def test_commodity_alias_services(default_facility):
    from apps.inventory.services import add_commodity_alias, remove_commodity_alias, merge_commodity
    from apps.inventory.models import Commodity, CommodityAlias
    from apps.inventory.services import create_commodity, create_grn
    from apps.locations.services import create_chamber, create_floor, create_block
    from apps.parties.services import create_party

    c1 = create_commodity(facility_id=default_facility.id, name="Jeera", unit="BAGS")
    c2 = create_commodity(facility_id=default_facility.id, name="Cumin", unit="BAGS")

    # 1. Adding an alias works
    alias = add_commodity_alias(commodity_id=c1.id, name="Jira")
    assert alias.name == "Jira"
    assert alias.commodity == c1

    # 2. An alias colliding with an existing commodity name is rejected
    with pytest.raises(ValidationError) as exc:
        add_commodity_alias(commodity_id=c1.id, name="Cumin")
    assert "already exists as a commodity" in str(exc.value)

    # 3. An alias colliding with another alias in the same facility is rejected
    with pytest.raises(ValidationError) as exc:
        add_commodity_alias(commodity_id=c2.id, name="Jira")
    assert "already exists as an alias" in str(exc.value)

    # 4. Same alias name IS allowed in a different facility
    from apps.facilities.models import Facility
    other_fac = Facility.objects.create(code="FAC-99", name="Other Facility", address="456 Cold Rd")
    other_c = create_commodity(facility_id=other_fac.id, name="Jeera", unit="BAGS")
    alias_other = add_commodity_alias(commodity_id=other_c.id, name="Jira")
    assert alias_other.name == "Jira"

    # 5. Case and whitespace variants are treated as collisions
    with pytest.raises(ValidationError):
        add_commodity_alias(commodity_id=c1.id, name=" jira ")
    with pytest.raises(ValidationError):
        add_commodity_alias(commodity_id=c1.id, name="JIRA")

    # 6. Reject alias equal to own commodity name
    with pytest.raises(ValidationError):
        add_commodity_alias(commodity_id=c1.id, name="Jeera")
    with pytest.raises(ValidationError):
        add_commodity_alias(commodity_id=c1.id, name=" jeera ")

    # 7. Merging a commodity into itself is rejected
    with pytest.raises(ValidationError):
        merge_commodity(source_commodity_id=c1.id, target_commodity_id=c1.id)

    # 8. Merging across facilities is rejected
    with pytest.raises(ValidationError):
        merge_commodity(source_commodity_id=c1.id, target_commodity_id=other_c.id)

    # 9. Merging moves all lots, leaves quantities untouched, creates back-alias, and deletes source
    party = create_party(facility_id=default_facility.id, name="API Farmer", type="DEPOSITOR")
    chamber = create_chamber(facility_id=default_facility.id, name="Chamber A")
    floor = create_floor(chamber_id=chamber.id, name="Floor A")
    block = create_block(floor_id=floor.id, name="Block A")

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=party.id,
        receipt_date=date(2026, 7, 25),
        items=[{
            "commodity_id": c2.id,
            "initial_qty": 150,
            "block_id": block.id,
        }]
    )
    lot = grn.lots.first()
    assert lot.commodity == c2
    assert lot.remaining_qty == 150

    source_alias = add_commodity_alias(commodity_id=c2.id, name="Cumin Powder")

    merge_commodity(source_commodity_id=c2.id, target_commodity_id=c1.id)

    assert not Commodity.objects.filter(id=c2.id).exists()

    lot.refresh_from_db()
    assert lot.commodity == c1
    assert lot.remaining_qty == 150

    assert CommodityAlias.objects.filter(commodity=c1, name="Cumin").exists()

    source_alias.refresh_from_db()
    assert source_alias.commodity == c1


