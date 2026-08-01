import pytest
from datetime import date
from decimal import Decimal
from django.utils import timezone

from apps.parties.services import create_party
from apps.inventory.services import create_commodity, create_grn
from apps.inventory.models import GRN
from apps.delivery.services import create_delivery_note, post_delivery_note
from apps.delivery.models import DeliveryNote
from apps.delivery.selectors import get_uninvoiced_delivery_lines
from apps.billing.services import compute_delivery_line_rent


@pytest.fixture
def test_party(default_facility):
    return create_party(
        facility_id=default_facility.id,
        name="Billing Test Farmer",
        type="DEPOSITOR"
    )


@pytest.fixture
def test_commodity(default_facility):
    return create_commodity(
        facility_id=default_facility.id,
        name="Green Peas",
        unit="BAGS"
    )



@pytest.mark.django_db
def test_compute_delivery_line_rent_real_chain(default_facility, test_party, test_commodity):
    """
    Test compute_delivery_line_rent against a real GRN -> Lot -> posted DN chain.
    Asserts exact Decimal rent output based on Lot.rent_rate_per_unit and DN dispatch_date.
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 1, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 500,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('12.00')
        }]
    )
    lot = grn.lots.first()

    dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 2, 3),  # 33 days stored -> multiplier 1.5
        status=DeliveryNote.Status.POSTED,
        lines=[{
            "lot_id": lot.id,
            "qty": 100
        }]
    )
    line = dn.lines.first()

    rent = compute_delivery_line_rent(line)
    # 100 bags * 12.00 rate * 1.5 multiplier (33 days) = 1800.00
    assert rent == Decimal('1800.00')


@pytest.mark.django_db
def test_two_withdrawals_same_lot_different_dates_different_multipliers(default_facility, test_party, test_commodity):
    """
    PROVES RULE 2: Rent is charged PER WITHDRAWAL, not per lot.
    Two withdrawals from the same lot at different dates bill different multipliers:
    - Withdrawal 1 on Day 19 (Jan 20): 30-day minimum floor applies -> multiplier 1.0
    - Withdrawal 2 on Day 49 (Feb 19): 49 days -> multiplier 2.0
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 1, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 1000,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('10.00')
        }]
    )
    lot = grn.lots.first()

    # Withdrawal 1: Day 19 (Jan 20) -> 19 days stored <= 30 -> multiplier 1.0
    dn1 = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 1, 20),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 100}]
    )
    line1 = dn1.lines.first()
    rent1 = compute_delivery_line_rent(line1)
    # 100 * 10 * 1.0 = 1000.00
    assert rent1 == Decimal('1000.00')

    # Withdrawal 2: Day 49 (Feb 19) -> 49 days stored -> multiplier 2.0
    dn2 = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 2, 19),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 100}]
    )
    line2 = dn2.lines.first()
    rent2 = compute_delivery_line_rent(line2)
    # 100 * 10 * 2.0 = 2000.00
    assert rent2 == Decimal('2000.00')


@pytest.mark.django_db
def test_get_uninvoiced_delivery_lines_filters_draft_and_invoiced(default_facility, test_party, test_commodity):
    """
    Asserts get_uninvoiced_delivery_lines:
    - Excludes lines from DRAFT delivery notes (RULE 3 - DRAFT DNs move zero stock and are not billable).
    - Excludes lines already marked invoiced_at.
    - Includes posted, uninvoiced delivery lines.
    """
    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 1, 1),
        status=GRN.Status.POSTED,
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 500,
            "unit_weight": Decimal('50.00'),
            "rent_rate_per_unit": Decimal('12.00')
        }]
    )
    lot = grn.lots.first()

    # DRAFT DN
    draft_dn = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 1, 15),
        status=DeliveryNote.Status.DRAFT,
        lines=[{"lot_id": lot.id, "qty": 50}]
    )

    # POSTED DN (Uninvoiced)
    posted_dn1 = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 1, 20),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 50}]
    )
    posted_line1 = posted_dn1.lines.first()

    # POSTED DN (Already Invoiced)
    posted_dn2 = create_delivery_note(
        facility_id=default_facility.id,
        party_id=test_party.id,
        dispatch_date=date(2026, 1, 25),
        status=DeliveryNote.Status.POSTED,
        lines=[{"lot_id": lot.id, "qty": 50}]
    )
    posted_line2 = posted_dn2.lines.first()
    posted_line2.invoiced_at = timezone.now()
    posted_line2.save()

    uninvoiced_lines = list(get_uninvoiced_delivery_lines(facility_id=default_facility.id))
    
    # Must contain ONLY posted_line1
    assert len(uninvoiced_lines) == 1
    assert uninvoiced_lines[0].id == posted_line1.id
