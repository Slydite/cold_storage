import pytest
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.parties.services import create_party
from apps.inventory.services import create_commodity, create_grn, withdraw_stock_from_lot
from apps.billing.models import RateCard, RentRun, RentRunLine
from apps.billing.services import (
    create_rate_card,
    create_rent_run,
    post_rent_run,
    cancel_rent_run
)


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
def test_create_rate_card_success(default_facility, test_commodity):
    rate_card = create_rate_card(
        facility_id=default_facility.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('50.00'),
        effective_from=date(2026, 1, 1)
    )

    assert rate_card.facility == default_facility
    assert rate_card.commodity == test_commodity
    assert rate_card.weight_category == RateCard.WeightCategory.KG_50
    assert rate_card.rate_per_bag_per_month == Decimal('50.00')
    assert rate_card.effective_from == date(2026, 1, 1)
    assert rate_card.is_active is True


@pytest.mark.django_db
def test_create_rate_card_duplicate_raises_validation_error(default_facility, test_commodity):
    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('50.00'),
        effective_from=date(2026, 1, 1)
    )

    with pytest.raises(ValidationError):
        create_rate_card(
            facility_id=default_facility.id,
            commodity_id=test_commodity.id,
            weight_category=RateCard.WeightCategory.KG_50,
            rate_per_bag_per_month=Decimal('60.00'),
            effective_from=date(2026, 1, 1)
        )


@pytest.mark.django_db
def test_create_rent_run_calculates_correct_amount(default_facility, test_party, test_commodity):
    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('50.00'),
        effective_from=date(2026, 1, 1)
    )

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00')
        }]
    )
    lot = grn.lots.first()

    period_start = date(2026, 7, 1)
    period_end = date(2026, 7, 31)

    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=period_start,
        period_end=period_end
    )

    assert rent_run.status == RentRun.Status.DRAFT
    assert rent_run.lines.count() == 1

    line = rent_run.lines.first()
    assert line.lot == lot
    assert line.party == test_party
    assert line.qty == 100
    assert line.weight_category == RateCard.WeightCategory.KG_50
    assert line.rate_per_bag_per_month == Decimal('50.00')
    assert line.days_stored == 31
    # 100 bags * 50.00 * 31 / 31 = 5000.00
    assert line.amount == Decimal('5000.00')


@pytest.mark.django_db
def test_create_rent_run_no_matching_rate_card_rolls_back(default_facility, test_party, test_commodity):
    # No rate card created
    create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00')
        }]
    )

    initial_run_count = RentRun.objects.count()
    initial_line_count = RentRunLine.objects.count()

    with pytest.raises(ValidationError) as exc:
        create_rent_run(
            facility_id=default_facility.id,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31)
        )

    assert "No active rate card" in str(exc.value)
    # Ensure atomicity — no rent run or lines created in DB
    assert RentRun.objects.count() == initial_run_count
    assert RentRunLine.objects.count() == initial_line_count


@pytest.mark.django_db
def test_create_rent_run_skips_zero_remaining_qty_lot(default_facility, test_party, test_commodity):
    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('50.00'),
        effective_from=date(2026, 1, 1)
    )

    grn = create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 50,
            "unit_weight": Decimal('50.00')
        }]
    )
    lot = grn.lots.first()

    # Fully withdraw stock
    withdraw_stock_from_lot(lot_id=lot.id, qty_to_withdraw=50)
    lot.refresh_from_db()
    assert lot.remaining_qty == 0

    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )

    assert rent_run.lines.count() == 0


@pytest.mark.django_db
def test_post_rent_run_success_and_repost_fails(default_facility, test_party, test_commodity):
    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('50.00'),
        effective_from=date(2026, 1, 1)
    )

    create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00')
        }]
    )

    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )
    assert rent_run.status == RentRun.Status.DRAFT

    posted_run = post_rent_run(rent_run_id=rent_run.id)
    assert posted_run.status == RentRun.Status.POSTED

    with pytest.raises(ValidationError) as exc:
        post_rent_run(rent_run_id=rent_run.id)
    assert "must be DRAFT" in str(exc.value)


@pytest.mark.django_db
def test_cancel_rent_run_success_and_cancel_posted_fails(default_facility, test_party, test_commodity):
    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('50.00'),
        effective_from=date(2026, 1, 1)
    )

    create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        items=[{
            "commodity_id": test_commodity.id,
            "initial_qty": 100,
            "unit_weight": Decimal('50.00')
        }]
    )

    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )

    cancelled_run = cancel_rent_run(rent_run_id=rent_run.id)
    assert cancelled_run.status == RentRun.Status.CANCELLED

    # Create another run and post it
    rent_run2 = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )
    post_rent_run(rent_run_id=rent_run2.id)

    with pytest.raises(ValidationError) as exc:
        cancel_rent_run(rent_run_id=rent_run2.id)
    assert "must be DRAFT" in str(exc.value)
