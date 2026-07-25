import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

from libs.lookups import get_facility_or_raise, get_party_or_raise
from apps.inventory.models import Commodity, Lot
from .models import RateCard, RentRun, RentRunLine
from .selectors import get_rent_run_by_id


def _resolve_rate_card(
    *,
    facility_id: int,
    party_id: int,
    commodity_id: int,
    weight_category: str,
    as_of: date
) -> tuple[RateCard | None, str | None]:
    """
    Resolve the applicable RateCard for a given facility, party, commodity, weight category, and date.

    PRECEDENCE RULE (Specificity over Recency):
    1. Party-specific rate card: Matches exact (facility_id, party_id, commodity_id, weight_category)
       with effective_from <= as_of and is_active=True, ordered by -effective_from.
    2. Default rate card: If no party-specific rate exists, falls back to party__isnull=True for
       (facility_id, commodity_id, weight_category) with effective_from <= as_of and is_active=True,
       ordered by -effective_from.
    3. None: If no active rate card matches either level, returns (None, None).

    Rationale:
    A negotiated party rate explicitly overrides any list/default rate for that party, regardless of
    whether a newer default rate card was created later. Specificity (party override) wins over recency.
    """
    if party_id:
        party_card = RateCard.objects.filter(
            facility_id=facility_id,
            party_id=party_id,
            commodity_id=commodity_id,
            weight_category=weight_category,
            is_active=True,
            effective_from__lte=as_of
        ).order_by('-effective_from').first()
        if party_card:
            return party_card, 'PARTY'

    default_card = RateCard.objects.filter(
        facility_id=facility_id,
        party__isnull=True,
        commodity_id=commodity_id,
        weight_category=weight_category,
        is_active=True,
        effective_from__lte=as_of
    ).order_by('-effective_from').first()
    if default_card:
        return default_card, 'DEFAULT'

    return None, None


@transaction.atomic
def create_rate_card(
    *,
    facility_id: int,
    commodity_id: int,
    weight_category: str,
    rate_per_bag_per_month: Decimal,
    effective_from: date,
    party_id: int | None = None,
    is_active: bool = True
) -> RateCard:
    """
    Create a new rate card for a commodity and weight category in a facility.
    Supports optional party_id for negotiated party-specific rate overrides.
    Validates facility, party (when provided), commodity, weight category, and rate amount.
    """
    facility = get_facility_or_raise(facility_id)

    party = None
    if party_id is not None:
        party = get_party_or_raise(party_id, facility)

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
        party=party,
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


def _compute_line(
    *,
    lot: Lot,
    period_start: date,
    period_end: date,
    min_billing_days: int,
    rate_card: RateCard,
    rate_source: str
) -> dict:
    """
    Compute line items for a single lot given a resolved rate_card and rate_source.
    Shared by create_rent_run and preview_rent_run to guarantee identical calculation logic.
    """
    overlap_start = max(lot.inward_date, period_start)
    overlap_end = period_end
    raw_days = (overlap_end - overlap_start).days + 1

    # Note: applying min_billing_days floor may cause days_stored to exceed actual period length,
    # which is intended for minimum billing periods.
    days_stored = max(raw_days, min_billing_days)
    weight_cat = _bucket_weight_category(lot.unit_weight)
    days_in_month = calendar.monthrange(period_start.year, period_start.month)[1]

    amount = (
        Decimal(lot.remaining_qty) * rate_card.rate_per_bag_per_month * Decimal(days_stored) / Decimal(days_in_month)
    ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return {
        'lot_id': lot.id,
        'lot_number': lot.lot_number,
        'commodity_id': lot.commodity_id,
        'commodity_name': lot.commodity.name,
        'party_id': lot.grn.party_id,
        'party_name': lot.grn.party.name,
        'qty': lot.remaining_qty,
        'weight_category': weight_cat,
        'rate_per_bag_per_month': rate_card.rate_per_bag_per_month,
        'days_stored': days_stored,
        'amount': amount,
        'rate_source': rate_source,
    }


@transaction.atomic
def create_rent_run(
    *,
    facility_id: int,
    period_start: date,
    period_end: date,
    party_id: int | None = None,
    commodity_id: int | None = None,
    chamber: str | None = None,
    min_billing_days: int = 0,
    notes: str = ''
) -> RentRun:
    """
    Calculate and create a DRAFT RentRun for a facility over a given date range.
    Queries candidate lots matching party/commodity/chamber filters, applies rate resolution
    and min_billing_days floor, and builds prorated lines.
    """
    facility = get_facility_or_raise(facility_id)

    if period_end < period_start:
        raise ValidationError("period_end cannot be before period_start.")

    if min_billing_days < 0:
        raise ValidationError("min_billing_days cannot be negative.")

    party = None
    if party_id is not None:
        party = get_party_or_raise(party_id, facility)

    commodity = None
    if commodity_id is not None:
        try:
            commodity = Commodity.objects.get(pk=commodity_id, facility=facility)
        except Commodity.DoesNotExist:
            raise ValidationError(f"Commodity with ID {commodity_id} does not exist in facility {facility_id}.")

    rent_run = RentRun(
        facility=facility,
        period_start=period_start,
        period_end=period_end,
        party=party,
        commodity=commodity,
        chamber=chamber or '',
        min_billing_days=min_billing_days,
        notes=notes or '',
        status=RentRun.Status.DRAFT
    )
    rent_run.full_clean()
    rent_run.save()

    candidate_lots = Lot.objects.select_for_update().select_related(
        'commodity', 'grn', 'grn__party'
    ).filter(
        facility_id=facility_id,
        grn__status='POSTED',
        inward_date__lte=period_end
    )
    if party_id is not None:
        candidate_lots = candidate_lots.filter(grn__party_id=party_id)
    if commodity_id is not None:
        candidate_lots = candidate_lots.filter(commodity_id=commodity_id)
    if chamber:
        candidate_lots = candidate_lots.filter(chamber__iexact=chamber)

    for lot in candidate_lots:
        if lot.remaining_qty == 0:
            continue

        overlap_start = max(lot.inward_date, period_start)
        overlap_end = period_end
        days_stored = (overlap_end - overlap_start).days + 1
        if days_stored <= 0:
            continue

        weight_cat = _bucket_weight_category(lot.unit_weight)
        rate_card, rate_source = _resolve_rate_card(
            facility_id=facility_id,
            party_id=lot.grn.party_id,
            commodity_id=lot.commodity_id,
            weight_category=weight_cat,
            as_of=period_end
        )

        if rate_card is None:
            raise ValidationError(
                f"No active rate card for commodity '{lot.commodity.name}' ({weight_cat}) in facility {facility_id} — cannot compute rent for Lot {lot.lot_number}."
            )

        line_dict = _compute_line(
            lot=lot,
            period_start=period_start,
            period_end=period_end,
            min_billing_days=min_billing_days,
            rate_card=rate_card,
            rate_source=rate_source
        )

        line = RentRunLine(
            rent_run=rent_run,
            lot=lot,
            party=lot.grn.party,
            qty=line_dict['qty'],
            weight_category=line_dict['weight_category'],
            rate_per_bag_per_month=line_dict['rate_per_bag_per_month'],
            days_stored=line_dict['days_stored'],
            amount=line_dict['amount']
        )
        line.full_clean()
        line.save()

    return get_rent_run_by_id(rent_run.id)


def preview_rent_run(
    *,
    facility_id: int,
    period_start: date,
    period_end: date,
    party_id: int | None = None,
    commodity_id: int | None = None,
    chamber: str | None = None,
    min_billing_days: int = 0
) -> dict:
    """
    Dry-run preview that computes rent run lines and missing rate cards without persisting anything.
    Side-effect free (no RentRun row, no lines created).
    Returns:
    {
        "lines": [ {lot_id, lot_number, commodity_name, party_id, party_name, qty, weight_category, rate_per_bag_per_month, days_stored, amount, rate_source} ],
        "total_amount": Decimal,
        "missing_rate_cards": [ {commodity_id, commodity_name, weight_category, lot_number} ]
    }
    """
    facility = get_facility_or_raise(facility_id)

    if period_end < period_start:
        raise ValidationError("period_end cannot be before period_start.")

    if min_billing_days < 0:
        raise ValidationError("min_billing_days cannot be negative.")

    if party_id is not None:
        get_party_or_raise(party_id, facility)

    if commodity_id is not None:
        try:
            Commodity.objects.get(pk=commodity_id, facility=facility)
        except Commodity.DoesNotExist:
            raise ValidationError(f"Commodity with ID {commodity_id} does not exist in facility {facility_id}.")

    candidate_lots = Lot.objects.select_related(
        'commodity', 'grn', 'grn__party'
    ).filter(
        facility_id=facility_id,
        grn__status='POSTED',
        inward_date__lte=period_end
    )
    if party_id is not None:
        candidate_lots = candidate_lots.filter(grn__party_id=party_id)
    if commodity_id is not None:
        candidate_lots = candidate_lots.filter(commodity_id=commodity_id)
    if chamber:
        candidate_lots = candidate_lots.filter(chamber__iexact=chamber)

    lines = []
    total_amount = Decimal('0.00')
    missing_rate_cards = []
    seen_missing = set()

    for lot in candidate_lots:
        if lot.remaining_qty == 0:
            continue

        overlap_start = max(lot.inward_date, period_start)
        overlap_end = period_end
        days_stored = (overlap_end - overlap_start).days + 1
        if days_stored <= 0:
            continue

        weight_cat = _bucket_weight_category(lot.unit_weight)
        rate_card, rate_source = _resolve_rate_card(
            facility_id=facility_id,
            party_id=lot.grn.party_id,
            commodity_id=lot.commodity_id,
            weight_category=weight_cat,
            as_of=period_end
        )

        if rate_card is None:
            missing_key = (lot.commodity_id, weight_cat)
            if missing_key not in seen_missing:
                seen_missing.add(missing_key)
                missing_rate_cards.append({
                    "commodity_id": lot.commodity_id,
                    "commodity_name": lot.commodity.name,
                    "weight_category": weight_cat,
                    "lot_number": lot.lot_number
                })
        else:
            line_dict = _compute_line(
                lot=lot,
                period_start=period_start,
                period_end=period_end,
                min_billing_days=min_billing_days,
                rate_card=rate_card,
                rate_source=rate_source
            )
            lines.append(line_dict)
            total_amount += line_dict['amount']

    return {
        "lines": lines,
        "total_amount": total_amount,
        "missing_rate_cards": missing_rate_cards
    }


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


def generate_rent_run_pdf(*, rent_run_id: int) -> str:
    """
    Generate a PDF summary report for a RentRun using ReportLab and store it in rent_run.pdf_file.
    Returns rent_run.pdf_file.url as a string.
    """
    try:
        rent_run = get_rent_run_by_id(rent_run_id)
    except RentRun.DoesNotExist:
        raise ValidationError(f"RentRun with ID {rent_run_id} does not exist.")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    elements = []

    facility = rent_run.facility

    # Title
    elements.append(Paragraph("<b>RENT RUN REPORT</b>", styles['Title']))
    elements.append(Spacer(1, 12))

    # Defensive field retrieval on facility
    gstin_val = getattr(facility, 'gstin', '')
    phone_val = getattr(facility, 'phone', '')
    facility_info = f"<b>{facility.name}</b><br/>{facility.address or facility.code}"
    if gstin_val:
        facility_info += f"<br/>GSTIN: {gstin_val}"
    if phone_val:
        facility_info += f"<br/>Phone: {phone_val}"

    party_filter = rent_run.party.name if rent_run.party else "All Parties"
    commodity_filter = rent_run.commodity.name if rent_run.commodity else "All Commodities"
    chamber_filter = rent_run.chamber if rent_run.chamber else "All Chambers"

    # Header section
    header_data = [
        [
            Paragraph(facility_info, styles['Normal']),
            Paragraph(
                f"<b>Run ID:</b> RentRun #{rent_run.id}<br/>"
                f"<b>Period:</b> {rent_run.period_start} to {rent_run.period_end}<br/>"
                f"<b>Status:</b> {rent_run.status}<br/>"
                f"<b>Party Filter:</b> {party_filter}<br/>"
                f"<b>Commodity Filter:</b> {commodity_filter}<br/>"
                f"<b>Chamber Filter:</b> {chamber_filter}<br/>"
                f"<b>Min Billing Days:</b> {rent_run.min_billing_days}",
                styles['Normal']
            )
        ]
    ]
    header_table = Table(header_data, colWidths=[270, 270])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 16))

    # Table of lines
    lines = rent_run.lines.all()
    table_data = [["Lot #", "Commodity", "Party", "Qty", "Weight Cat.", "Rate (₹)", "Days", "Amount (₹)"]]

    total_amount = Decimal('0.00')
    for line in lines:
        total_amount += line.amount
        table_data.append([
            line.lot.lot_number,
            line.lot.commodity.name,
            line.party.name,
            str(line.qty),
            line.weight_category,
            f"{line.rate_per_bag_per_month:.2f}",
            str(line.days_stored),
            f"{line.amount:.2f}"
        ])

    table_data.append(["Total", "", "", "", "", "", "", f"{total_amount:.2f}"])

    items_table = Table(table_data, colWidths=[65, 75, 90, 40, 60, 60, 40, 110])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(items_table)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f"RentRun_{rent_run.id}.pdf"
    with transaction.atomic():
        rent_run.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

    return rent_run.pdf_file.url

