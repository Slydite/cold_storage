import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.core.exceptions import ValidationError
from libs.lookups import get_facility_or_raise
from apps.inventory.models import Commodity, Lot
from .models import RateCard, RentRun, RentRunLine
from .selectors import get_rent_run_by_id


@transaction.atomic
def create_rate_card(
    *,
    facility_id: int,
    commodity_id: int,
    weight_category: str,
    rate_per_bag_per_month: Decimal,
    effective_from: date,
    is_active: bool = True
) -> RateCard:
    """
    Create a new rate card for a commodity and weight category in a facility.
    Validates facility, commodity, weight category, and rate amount.
    """
    facility = get_facility_or_raise(facility_id)

    try:
        commodity = Commodity.objects.get(pk=commodity_id, facility=facility)
    except Commodity.DoesNotExist:
        raise ValidationError(f"Commodity with ID {commodity_id} does not exist in facility {facility_id}.")

    if weight_category not in RateCard.WeightCategory.values:
        raise ValidationError(f"Invalid weight category: {weight_category}. Allowed: {RateCard.WeightCategory.values}")

    rate_per_bag_per_month = Decimal(str(rate_per_bag_per_month))
    if rate_per_bag_per_month <= Decimal('0.00'):
        raise ValidationError("Rate per bag per month must be greater than 0.")

    rate_card = RateCard(
        facility=facility,
        commodity=commodity,
        weight_category=weight_category,
        rate_per_bag_per_month=rate_per_bag_per_month,
        effective_from=effective_from,
        is_active=is_active
    )
    rate_card.full_clean()
    rate_card.save()
    return rate_card


def _bucket_weight_category(unit_weight: Decimal) -> str:
    """
    Private helper to map bag unit_weight (in kg) to RateCard.WeightCategory.
    Thresholds:
    - unit_weight <= 25 kg -> KG_20 (reasonable threshold for ~20 kg bags)
    - 25 kg < unit_weight <= 60 kg -> KG_50 (reasonable threshold for ~50 kg bags)
    - > 60 kg -> OTHER
    """
    unit_weight = Decimal(str(unit_weight))
    if unit_weight <= Decimal('25'):
        return RateCard.WeightCategory.KG_20
    elif unit_weight <= Decimal('60'):
        return RateCard.WeightCategory.KG_50
    else:
        return RateCard.WeightCategory.OTHER


@transaction.atomic
def create_rent_run(
    *,
    facility_id: int,
    period_start: date,
    period_end: date
) -> RentRun:
    """
    Calculate and create a DRAFT RentRun for a facility over a given date range.
    Queries candidate lots, checks applicable RateCards, and builds prorated lines.
    """
    facility = get_facility_or_raise(facility_id)

    if period_end < period_start:
        raise ValidationError("period_end cannot be before period_start.")

    rent_run = RentRun(
        facility=facility,
        period_start=period_start,
        period_end=period_end,
        status=RentRun.Status.DRAFT
    )
    rent_run.full_clean()
    rent_run.save()

    # Known simplification per standing.md §3 & prompt: lot remaining_qty is taken as of run creation time.
    # A lot withdrawn mid-period is billed on its post-withdrawal remaining_qty for the whole period.
    # We do not reconstruct historical quantities from DN records.
    candidate_lots = Lot.objects.select_for_update().select_related(
        'commodity', 'grn', 'grn__party'
    ).filter(
        facility_id=facility_id,
        grn__status='POSTED',
        inward_date__lte=period_end
    )

    # Days in month assumption: period_start and period_end fall within the same calendar month
    # (monthly billing cycle per standing.md §7). Using period_start's month for days_in_month calculation.
    days_in_month = calendar.monthrange(period_start.year, period_start.month)[1]

    for lot in candidate_lots:
        if lot.remaining_qty == 0:
            continue

        overlap_start = max(lot.inward_date, period_start)
        overlap_end = period_end
        days_stored = (overlap_end - overlap_start).days + 1
        if days_stored <= 0:
            continue

        weight_cat = _bucket_weight_category(lot.unit_weight)

        rate_card = RateCard.objects.filter(
            facility_id=facility_id,
            commodity_id=lot.commodity_id,
            weight_category=weight_cat,
            is_active=True,
            effective_from__lte=period_end
        ).order_by('-effective_from').first()

        if rate_card is None:
            raise ValidationError(
                f"No active rate card for commodity '{lot.commodity.name}' ({weight_cat}) in facility {facility_id} — cannot compute rent for Lot {lot.lot_number}."
            )

        amount = (
            Decimal(lot.remaining_qty) * rate_card.rate_per_bag_per_month * Decimal(days_stored) / Decimal(days_in_month)
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        line = RentRunLine(
            rent_run=rent_run,
            lot=lot,
            party=lot.grn.party,
            qty=lot.remaining_qty,
            weight_category=weight_cat,
            rate_per_bag_per_month=rate_card.rate_per_bag_per_month,
            days_stored=days_stored,
            amount=amount
        )
        line.full_clean()
        line.save()

    return get_rent_run_by_id(rent_run.id)


@transaction.atomic
def post_rent_run(*, rent_run_id: int) -> RentRun:
    """
    Transition a RentRun from DRAFT to POSTED using row lock.
    """
    try:
        rent_run = RentRun.objects.select_for_update().get(pk=rent_run_id)
    except RentRun.DoesNotExist:
        raise ValidationError(f"RentRun with ID {rent_run_id} does not exist.")

    if rent_run.status != RentRun.Status.DRAFT:
        raise ValidationError(f"Cannot post RentRun: current status is '{rent_run.status}', must be DRAFT.")

    rent_run.status = RentRun.Status.POSTED
    rent_run.full_clean()
    rent_run.save()
    return get_rent_run_by_id(rent_run.id)


@transaction.atomic
def cancel_rent_run(*, rent_run_id: int) -> RentRun:
    """
    Transition a RentRun from DRAFT to CANCELLED using row lock.
    """
    try:
        rent_run = RentRun.objects.select_for_update().get(pk=rent_run_id)
    except RentRun.DoesNotExist:
        raise ValidationError(f"RentRun with ID {rent_run_id} does not exist.")

    if rent_run.status != RentRun.Status.DRAFT:
        raise ValidationError(f"Cannot cancel RentRun: current status is '{rent_run.status}', must be DRAFT.")

    rent_run.status = RentRun.Status.CANCELLED
    rent_run.save()
    return get_rent_run_by_id(rent_run.id)
