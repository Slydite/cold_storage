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
    preview_rent_run,
    post_rent_run,
    cancel_rent_run,
    generate_rent_run_pdf
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
def test_party2(default_facility):
    return create_party(
        facility_id=default_facility.id,
        name="Second Farmer",
        code="FARM-02",
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
    assert rate_card.party is None
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
def test_party_specific_rate_beats_default_rate(default_facility, test_party, test_party2, test_commodity):
    # Default rate card: 50.00
    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('50.00'),
        effective_from=date(2026, 1, 1)
    )

    # Party 1 negotiated override: 40.00
    create_rate_card(
        facility_id=default_facility.id,
        party_id=test_party.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('40.00'),
        effective_from=date(2026, 1, 1)
    )

    # GRN for Party 1
    create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        items=[{"commodity_id": test_commodity.id, "initial_qty": 100, "unit_weight": Decimal('50.00')}]
    )

    # GRN for Party 2 (no override)
    create_grn(
        facility_id=default_facility.id,
        party_id=test_party2.id,
        receipt_date=date(2026, 7, 1),
        items=[{"commodity_id": test_commodity.id, "initial_qty": 100, "unit_weight": Decimal('50.00')}]
    )

    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )

    lines_by_party = {line.party_id: line for line in rent_run.lines.all()}
    # Party 1 uses negotiated rate (40.00 * 100 = 4000.00)
    assert lines_by_party[test_party.id].rate_per_bag_per_month == Decimal('40.00')
    assert lines_by_party[test_party.id].amount == Decimal('4000.00')

    # Party 2 uses default rate (50.00 * 100 = 5000.00)
    assert lines_by_party[test_party2.id].rate_per_bag_per_month == Decimal('50.00')
    assert lines_by_party[test_party2.id].amount == Decimal('5000.00')


@pytest.mark.django_db
def test_newer_party_specific_rate_supersedes_older(default_facility, test_party, test_commodity):
    create_rate_card(
        facility_id=default_facility.id,
        party_id=test_party.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('40.00'),
        effective_from=date(2026, 1, 1)
    )
    create_rate_card(
        facility_id=default_facility.id,
        party_id=test_party.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('35.00'),
        effective_from=date(2026, 6, 1)
    )

    create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        items=[{"commodity_id": test_commodity.id, "initial_qty": 100, "unit_weight": Decimal('50.00')}]
    )

    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )

    line = rent_run.lines.first()
    assert line.rate_per_bag_per_month == Decimal('35.00')
    assert line.amount == Decimal('3500.00')


@pytest.mark.django_db
def test_older_party_override_beats_newer_default_rate(default_facility, test_party, test_commodity):
    # Older party override
    create_rate_card(
        facility_id=default_facility.id,
        party_id=test_party.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('40.00'),
        effective_from=date(2026, 1, 1)
    )
    # Newer default rate
    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('60.00'),
        effective_from=date(2026, 6, 1)
    )

    create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        items=[{"commodity_id": test_commodity.id, "initial_qty": 100, "unit_weight": Decimal('50.00')}]
    )

    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )

    line = rent_run.lines.first()
    assert line.rate_per_bag_per_month == Decimal('40.00')
    assert line.amount == Decimal('4000.00')


@pytest.mark.django_db
def test_min_billing_days_floors_short_stay(default_facility, test_party, test_commodity):
    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('31.00'),
        effective_from=date(2026, 1, 1)
    )

    # Inward on 29th July (3 days stored in July: 29, 30, 31)
    create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 29),
        items=[{"commodity_id": test_commodity.id, "initial_qty": 100, "unit_weight": Decimal('50.00')}]
    )

    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31),
        min_billing_days=15
    )

    line = rent_run.lines.first()
    assert line.days_stored == 15
    # 100 bags * 31.00 * 15 / 31 = 1500.00
    assert line.amount == Decimal('1500.00')


@pytest.mark.django_db
def test_party_id_and_commodity_id_filters_narrow_lots(default_facility, test_party, test_party2, test_commodity):
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
        items=[{"commodity_id": test_commodity.id, "initial_qty": 100, "unit_weight": Decimal('50.00')}]
    )
    create_grn(
        facility_id=default_facility.id,
        party_id=test_party2.id,
        receipt_date=date(2026, 7, 1),
        items=[{"commodity_id": test_commodity.id, "initial_qty": 50, "unit_weight": Decimal('50.00')}]
    )

    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31),
        party_id=test_party.id
    )

    assert rent_run.lines.count() == 1
    assert rent_run.lines.first().party == test_party


@pytest.mark.django_db
def test_preview_rent_run_does_not_persist_and_reports_missing_rate_cards(default_facility, test_party, test_party2, test_commodity):
    comm2 = create_commodity(facility_id=default_facility.id, name="Peas", code="PEAS-02", unit="BAGS")

    # Rate card for test_commodity only
    create_rate_card(
        facility_id=default_facility.id,
        commodity_id=test_commodity.id,
        weight_category=RateCard.WeightCategory.KG_50,
        rate_per_bag_per_month=Decimal('50.00'),
        effective_from=date(2026, 1, 1)
    )

    # GRN 1 with rate card
    create_grn(
        facility_id=default_facility.id,
        party_id=test_party.id,
        receipt_date=date(2026, 7, 1),
        items=[{"commodity_id": test_commodity.id, "initial_qty": 100, "unit_weight": Decimal('50.00')}]
    )

    # GRN 2 without rate card
    create_grn(
        facility_id=default_facility.id,
        party_id=test_party2.id,
        receipt_date=date(2026, 7, 1),
        items=[{"commodity_id": comm2.id, "initial_qty": 50, "unit_weight": Decimal('50.00')}]
    )

    initial_run_count = RentRun.objects.count()
    initial_line_count = RentRunLine.objects.count()

    preview = preview_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )

    # DB untouched!
    assert RentRun.objects.count() == initial_run_count
    assert RentRunLine.objects.count() == initial_line_count

    assert len(preview['lines']) == 1
    assert preview['lines'][0]['rate_source'] == 'DEFAULT'
    assert preview['lines'][0]['amount'] == Decimal('5000.00')

    assert len(preview['missing_rate_cards']) == 1
    assert preview['missing_rate_cards'][0]['commodity_id'] == comm2.id

    # create_rent_run on same inputs raises ValidationError and rolls back
    with pytest.raises(ValidationError):
        create_rent_run(
            facility_id=default_facility.id,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 31)
        )

    assert RentRun.objects.count() == initial_run_count
    assert RentRunLine.objects.count() == initial_line_count


@pytest.mark.django_db
def test_generate_rent_run_pdf(default_facility, test_party, test_commodity):
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
        items=[{"commodity_id": test_commodity.id, "initial_qty": 100, "unit_weight": Decimal('50.00')}]
    )

    rent_run = create_rent_run(
        facility_id=default_facility.id,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31)
    )

    pdf_url = generate_rent_run_pdf(rent_run_id=rent_run.id)
    assert pdf_url is not None
    rent_run.refresh_from_db()
    assert bool(rent_run.pdf_file) is True
    assert rent_run.pdf_file.read().startswith(b'%PDF')


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

