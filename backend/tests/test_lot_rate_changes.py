import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.test import APIClient

from apps.parties.services import create_party
from apps.inventory.services import (
    create_commodity,
    create_grn,
    add_lot_rate_change,
    remove_lot_rate_change,
    bulk_add_rate_change
)
from apps.inventory.models import GRN, LotRateChange, Lot
from apps.delivery.services import create_delivery_note, post_delivery_note
from apps.delivery.models import DeliveryNote, DeliveryLine
from apps.billing.services import (
    compute_delivery_line_rent,
    compute_segmented_rent,
    compute_segmented_rent_details
)
from apps.invoicing.services import generate_invoices_for_uninvoiced_deliveries
from apps.invoicing.models import Invoice, InvoiceLine


@pytest.fixture
def lot_party(default_facility):
    return create_party(
        facility_id=default_facility.id,
        name="Rate Change Farmer",
        type="DEPOSITOR"
    )


@pytest.fixture
def lot_commodity(default_facility):
    return create_commodity(
        facility_id=default_facility.id,
        name="Potato",
        unit="BAGS"
    )


@pytest.mark.django_db
def test_rent_across_one_rate_change(default_facility, lot_party, lot_commodity, default_block):
    """
    1. Rent across one rate change equals the sum of the two segments.
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=lot_party.id,
        receipt_date=date(2026, 1, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": lot_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('10.00'),  # intake rate
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    # Add rate change effective 2026-02-01 to 12.00
    rc = add_lot_rate_change(
        lot_id=lot.id,
        rate_per_unit=Decimal('12.00'),
        effective_from=date(2026, 2, 1),
        note="Increase rate"
    )

    # Dispatch on 2026-03-01
    # Segment 1: 2026-01-01 to 2026-02-01 (31 days -> 1.5 months * 10 * 100 = 1500)
    # Segment 2: 2026-02-01 to 2026-03-01 (28 days -> 1.0 month * 12 * 100 = 1200)
    # Total expected rent = 1500 + 1200 = 2700
    rent = compute_segmented_rent(
        qty=100,
        intake_rate=Decimal('10.00'),
        rate_changes=[rc],
        inward_date=date(2026, 1, 1),
        out_date=date(2026, 3, 1)
    )
    assert rent == Decimal('2700.00')


@pytest.mark.django_db
def test_rate_change_after_dispatch_ignored(default_facility, lot_party, lot_commodity, default_block):
    """
    2. A rate change dated after the dispatch date is ignored.
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=lot_party.id,
        receipt_date=date(2026, 1, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": lot_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('10.00'),
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    # Rate change after dispatch (2026-02-15)
    rc = add_lot_rate_change(
        lot_id=lot.id,
        rate_per_unit=Decimal('12.00'),
        effective_from=date(2026, 2, 15),
        note="Future change"
    )

    # Dispatch on 2026-02-01 (31 days -> 1.5 months)
    rent = compute_segmented_rent(
        qty=100,
        intake_rate=Decimal('10.00'),
        rate_changes=[rc],
        inward_date=date(2026, 1, 1),
        out_date=date(2026, 2, 1)
    )
    # Ignored because 2026-02-15 >= dispatch 2026-02-01
    # 100 * 10 * 1.5 = 1500
    assert rent == Decimal('1500.00')


@pytest.mark.django_db
def test_rate_change_on_inward_date_replaces_intake_rate(default_facility, lot_party, lot_commodity, default_block):
    """
    3. A rate change effective exactly on inward_date replaces the intake rate.
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=lot_party.id,
        receipt_date=date(2026, 1, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": lot_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('10.00'),
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    rc = add_lot_rate_change(
        lot_id=lot.id,
        rate_per_unit=Decimal('15.00'),
        effective_from=date(2026, 1, 1),
        note="Replace intake"
    )

    rent = compute_segmented_rent(
        qty=100,
        intake_rate=Decimal('10.00'),
        rate_changes=[rc],
        inward_date=date(2026, 1, 1),
        out_date=date(2026, 2, 1)
    )
    # 100 * 15 * 1.5 = 2250
    assert rent == Decimal('2250.00')


@pytest.mark.django_db
def test_stay_with_no_rate_changes_bills_exactly_as_today(default_facility, lot_party, lot_commodity, default_block):
    """
    4. A stay with no rate changes bills exactly as it does today (assert against current expected value).
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=lot_party.id,
        receipt_date=date(2026, 1, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": lot_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('12.00'),
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=lot_party.id,
        dispatch_date=date(2026, 2, 3),  # 33 days stored -> multiplier 1.5
        status=DeliveryNote.Status.POSTED,
        lines=[{
            "lot_id": lot.id,
            "qty": 100
        }]
    )
    line = dn.lines.first()

    # 100 bags * 12.00 rate * 1.5 multiplier (33 days) = 1800.00
    rent = compute_delivery_line_rent(line)
    assert rent == Decimal('1800.00')


@pytest.mark.django_db
def test_one_month_minimum_applies_to_whole_stay(default_facility, lot_party, lot_commodity, default_block):
    """
    5. The one-month minimum applies to the whole stay, not per segment.
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=lot_party.id,
        receipt_date=date(2026, 1, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": lot_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('10.00'),
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    # Very short stay of 4 days total
    # If we did 1 month minimum per segment, it would bill 2 months.
    # If we sum first: segment 1 (2 days -> 0.133 month period -> 0.5 rounded), segment 2 (2 days -> 0.5 rounded). Total = 1.0.
    # What if it's 0 days or less? It should bill 1.0 month of starting rate.
    rent = compute_segmented_rent(
        qty=100,
        intake_rate=Decimal('10.00'),
        rate_changes=[],
        inward_date=date(2026, 1, 1),
        out_date=date(2026, 1, 5)  # 4 days -> 0.5 month. Falls back to 1.0 month minimum
    )
    assert rent == Decimal('1000.00')  # 100 * 10 * 1.0 = 1000.00


@pytest.mark.django_db
def test_effective_from_before_inward_date_rejected(default_facility, lot_party, lot_commodity, default_block):
    """
    6. effective_from before inward_date is rejected.
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=lot_party.id,
        receipt_date=date(2026, 1, 10),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": lot_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('10.00'),
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    with pytest.raises(DjangoValidationError) as excinfo:
        add_lot_rate_change(
            lot_id=lot.id,
            rate_per_unit=Decimal('12.00'),
            effective_from=date(2026, 1, 9),  # before inward_date 2026-01-10
            note="Invalid date"
        )
    assert "before the lot's inward date" in str(excinfo.value)


@pytest.mark.django_db
def test_duplicate_effective_from_rejected(default_facility, lot_party, lot_commodity, default_block):
    """
    7. A duplicate effective_from on one lot is rejected.
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=lot_party.id,
        receipt_date=date(2026, 1, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": lot_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('10.00'),
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    add_lot_rate_change(
        lot_id=lot.id,
        rate_per_unit=Decimal('12.00'),
        effective_from=date(2026, 2, 1),
        note="First rate change"
    )

    with pytest.raises(DjangoValidationError) as excinfo:
        add_lot_rate_change(
            lot_id=lot.id,
            rate_per_unit=Decimal('13.00'),
            effective_from=date(2026, 2, 1),  # duplicate
            note="Second rate change"
        )
    assert "already scheduled" in str(excinfo.value)


@pytest.mark.django_db
def test_rate_change_over_already_invoiced_period_rejected(default_facility, lot_party, lot_commodity, default_block):
    """
    8. A rate change over an already-invoiced period is rejected.
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=lot_party.id,
        receipt_date=date(2026, 1, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": lot_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('10.00'),
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    rc = add_lot_rate_change(
        lot_id=lot.id,
        rate_per_unit=Decimal('11.00'),
        effective_from=date(2026, 2, 1),
        note="Add before invoice"
    )

    # Dispatch stock on 2026-03-01
    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=lot_party.id,
        dispatch_date=date(2026, 3, 1),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 50}]
    )

    # Generate invoice -> DeliveryLine.invoiced_at will be set
    invoices = generate_invoices_for_uninvoiced_deliveries(facility_id=default_facility.id)
    assert len(invoices) == 1
    assert invoices[0].lines.count() > 0

    # Try to add a rate change effective on or before 2026-03-01 (the dispatch date)
    with pytest.raises(DjangoValidationError) as excinfo:
        add_lot_rate_change(
            lot_id=lot.id,
            rate_per_unit=Decimal('15.00'),
            effective_from=date(2026, 2, 15),  # <= 2026-03-01
            note="Too late"
        )
    assert "Cannot alter rate for a period already billed" in str(excinfo.value)

    # Try to remove the existing rate change rc which is effective 2026-02-01 (<= 2026-03-01)
    with pytest.raises(DjangoValidationError) as excinfo2:
        remove_lot_rate_change(rate_change_id=rc.id)
    assert "Cannot remove rate change: the lot has already been invoiced" in str(excinfo2.value)


@pytest.mark.django_db
def test_entry_date_and_effective_date_independent(default_facility, lot_party, lot_commodity, default_block):
    """
    9. Entry date and effective date are independent: a change created today but effective last month bills last month at the new rate.
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=lot_party.id,
        receipt_date=date(2026, 1, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": lot_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('10.00'),
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    # Rate change is effective last month (say 2026-01-15)
    rc = add_lot_rate_change(
        lot_id=lot.id,
        rate_per_unit=Decimal('15.00'),
        effective_from=date(2026, 1, 15)
    )

    # Created_at is now/today (2026-08-02 / timezone.now()), but effective_from is 2026-01-15.
    # Rent for dispatch on 2026-02-01:
    # Segment 1: 2026-01-01 to 2026-01-15 (14 days -> 0.5 month * 10 * 100 = 500)
    # Segment 2: 2026-01-15 to 2026-02-01 (17 days -> 1.0 month * 15 * 100 = 1500)
    # Total = 2000
    rent = compute_segmented_rent(
        qty=100,
        intake_rate=Decimal('10.00'),
        rate_changes=[rc],
        inward_date=date(2026, 1, 1),
        out_date=date(2026, 2, 1)
    )
    assert rent == Decimal('2000.00')


@pytest.mark.django_db
def test_bulk_add_rate_change_skips_and_applies(default_facility, lot_party, lot_commodity, default_block):
    """
    10. Bulk change applies to matching lots and reports skips with reasons.
    """
    # Create two lots
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=lot_party.id,
        receipt_date=date(2026, 1, 1),
        status=GRN.Status.POSTED,
        items=[
            {
                "commodity_id": lot_commodity.id,
                "initial_qty": 100,
                "unit_weight": Decimal('50.00'),
                "rent_rate_per_unit": Decimal('10.00'),
                "block_id": default_block.id,
            },
            {
                "commodity_id": lot_commodity.id,
                "initial_qty": 200,
                "unit_weight": Decimal('50.00'),
                "rent_rate_per_unit": Decimal('10.00'),
                "block_id": default_block.id,
            }
        ]
    )
    lots = list(grn.lots.all())
    lot1 = lots[0]
    lot2 = lots[1]

    # Lot 1 is invoiced on dispatch 2026-02-01
    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=lot_party.id,
        dispatch_date=date(2026, 2, 1),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot1.id, "qty": 50}]
    )
    generate_invoices_for_uninvoiced_deliveries(facility_id=default_facility.id)

    # Now, bulk add a rate change effective 2026-01-15 (before/on dispatch date for lot1, so lot1 should fail validation and be skipped)
    # Lot 2 has no invoicing, so it should succeed.
    result = bulk_add_rate_change(
        facility_id=default_facility.id,
        rate_per_unit=Decimal('15.00'),
        effective_from=date(2026, 1, 15),
        note="Bulk adjust"
    )

    assert result['applied_count'] == 1
    assert result['skipped_count'] == 1
    assert len(result['skipped_details']) == 1
    assert result['skipped_details'][0]['lot_id'] == lot1.id
    assert "Cannot alter rate for a period already billed" in result['skipped_details'][0]['reason']


@pytest.mark.django_db
def test_invoicing_spanned_stay_produces_two_lines(default_facility, lot_party, lot_commodity, default_block):
    """
    11. Invoicing a stay that spans a change produces two invoice lines with the right periods and rates.
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=lot_party.id,
        receipt_date=date(2026, 1, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": lot_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('10.00'),
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    # Rate change effective 2026-02-01
    add_lot_rate_change(
        lot_id=lot.id,
        rate_per_unit=Decimal('12.00'),
        effective_from=date(2026, 2, 1),
        note="Inc rate"
    )

    # Dispatch on 2026-03-01
    create_delivery_note(
        facility_id=default_facility.id,
        party_id=lot_party.id,
        dispatch_date=date(2026, 3, 1),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 100}]
    )

    # Generate invoice
    invoices = generate_invoices_for_uninvoiced_deliveries(facility_id=default_facility.id)
    assert len(invoices) == 1
    invoice = invoices[0]

    # Find the rent invoice lines
    rent_lines = list(invoice.lines.filter(charge_type=InvoiceLine.ChargeType.RENT).order_by('period_from'))
    assert len(rent_lines) == 2

    # Verify periods and rates
    assert rent_lines[0].period_from == date(2026, 1, 1)
    assert rent_lines[0].period_to == date(2026, 2, 1)
    assert rent_lines[0].rate_per_unit == Decimal('10.00')
    assert rent_lines[0].amount == Decimal('1500.00')  # 1.5 * 10 * 100

    assert rent_lines[1].period_from == date(2026, 2, 1)
    assert rent_lines[1].period_to == date(2026, 3, 1)
    assert rent_lines[1].rate_per_unit == Decimal('12.00')
    assert rent_lines[1].amount == Decimal('1200.00')  # 1.0 * 12 * 100

    assert "Segment:" in rent_lines[0].description
    assert "Segment:" in rent_lines[1].description


@pytest.mark.django_db
def test_endpoints_require_authentication(default_facility, lot_party, lot_commodity, default_block):
    """
    12. Endpoints require authentication.
    """
    # Use a fresh, unauthenticated APIClient
    client = APIClient()

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=lot_party.id,
        receipt_date=date(2026, 1, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": lot_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('10.00'),
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    # 1. Add rate change
    response = client.post(f'/api/lots/{lot.id}/rate-changes/', {
        "rate_per_unit": "12.00",
        "effective_from": "2026-02-01"
    })
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # 2. Remove rate change (using a dummy ID like 999)
    response = client.delete(f'/api/lots/{lot.id}/rate-changes/999/')
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # 3. Bulk rate change
    response = client.post('/api/lots/bulk-rate-change/', {
        "facility_id": default_facility.id,
        "rate_per_unit": "12.00",
        "effective_from": "2026-02-01"
    })
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_authenticated_endpoints_lifecycle(auth_client, default_facility, lot_party, lot_commodity, default_block):
    """
    Verify authenticated endpoint CRUD operations and behavior.
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=lot_party.id,
        receipt_date=date(2026, 1, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": lot_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('10.00'),
            "block_id": default_block.id,
        }]
    )
    lot = grn.lots.first()

    # POST rate change
    response = auth_client.post(f'/api/lots/{lot.id}/rate-changes/', {
        "rate_per_unit": "12.00",
        "effective_from": "2026-02-01",
        "note": "API test"
    })
    assert response.status_code == status.HTTP_201_CREATED
    rc_id = response.data['id']
    assert response.data['rate_per_unit'] == "12.00"
    assert response.data['effective_from'] == "2026-02-01"

    # Get lot detail and verify rate_changes list is populated
    response_get = auth_client.get(f'/api/lots/{lot.id}/')
    assert response_get.status_code == status.HTTP_200_OK
    assert len(response_get.data['rate_changes']) == 1
    assert response_get.data['rate_changes'][0]['id'] == rc_id

    # POST bulk change
    response_bulk = auth_client.post('/api/lots/bulk-rate-change/', {
        "facility_id": default_facility.id,
        "rate_per_unit": "15.00",
        "effective_from": "2026-02-15",
        "note": "Bulk API"
    })
    assert response_bulk.status_code == status.HTTP_200_OK
    assert response_bulk.data['applied_count'] == 1

    # DELETE rate change
    response_del = auth_client.delete(f'/api/lots/{lot.id}/rate-changes/{rc_id}/')
    assert response_del.status_code == status.HTTP_204_NO_CONTENT
