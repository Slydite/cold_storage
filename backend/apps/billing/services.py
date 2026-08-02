from datetime import date
from decimal import Decimal, ROUND_HALF_UP


def billable_multiplier(days_stored: int) -> Decimal:
    """
    Calculate the rent multiplier based on days in storage.

    A storage month is exactly 30 x 24 hours (30 days). Rent is charged in
    half-month (15-day) steps, rounded up, with a minimum of one month.
    A stay of exactly 30 days bills one month.

    Rent is calculated as:
    period = max(1.0, ceil(days_stored / 15) / 2)

    No grace period is allowed.
    """
    if days_stored < 0:
        days_stored = 0
    # Use integer arithmetic for the ceiling to avoid float rounding drift:
    # ceil(days_stored / 15) is equivalent to -(-days_stored // 15)
    ceil_days_div_15 = -(-days_stored // 15)
    period = Decimal(ceil_days_div_15) / Decimal('2')
    return max(Decimal('1.0'), period)


def days_stored(inward_date: date, out_date: date) -> int:
    """
    Calculate the number of elapsed days stock was stored between inward_date and out_date.

    Months are defined as 30 x 24 hours (30 days). Under this rule, time is counted
    as elapsed days from the GRN's inward_date to the delivery note's dispatch_date (out_date),
    without including the +1 day.

    If out_date is before inward_date, this function returns 0 days.
    """
    if out_date < inward_date:
        return 0
    return (out_date - inward_date).days


def compute_line_rent(
    *,
    qty: int,
    rate_per_unit_per_month: Decimal,
    inward_date: date,
    out_date: date
) -> Decimal:
    """
    Compute total rent for a specific quantity withdrawn between inward_date and out_date (RULE 1 & 2).

    Formula:
    rent = qty * rate_per_unit_per_month * billable_multiplier(days_stored(inward_date, out_date))
    Quantized to 2 decimal places using ROUND_HALF_UP.
    """
    days = days_stored(inward_date, out_date)
    multiplier = billable_multiplier(days)
    amount = Decimal(qty) * Decimal(str(rate_per_unit_per_month)) * multiplier
    return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def compute_delivery_line_rent(delivery_line) -> Decimal:
    """
    Convenience wrapper pulling quantity from delivery_line, rate and inward_date from
    delivery_line.lot, and out_date from delivery_line.delivery_note.dispatch_date.
    Uses the new segmented path, reading the lot's rate changes.
    """
    lot = delivery_line.lot
    return compute_segmented_rent(
        qty=delivery_line.qty,
        intake_rate=lot.rent_rate_per_unit,
        rate_changes=lot.rate_changes.all(),
        inward_date=lot.inward_date,
        out_date=delivery_line.delivery_note.dispatch_date,
    )


def compute_segmented_rent_details(
    *,
    qty: int,
    intake_rate: Decimal,
    rate_changes: list,
    inward_date: date,
    out_date: date
) -> list:
    """
    Compute details of rent across rate segments.
    Each segment is a dictionary containing:
      - 'period_from': date
      - 'period_to': date
      - 'rate_per_unit': Decimal
      - 'days_stored': int
      - 'period': Decimal
      - 'amount': Decimal
    """
    # 1. Determine starting rate (rate in force on inward_date).
    # A rate change effective exactly on inward_date replaces the intake rate.
    # Any rate change before inward_date is ignored.
    starting_rate = intake_rate
    for rc in rate_changes:
        if rc.effective_from == inward_date:
            starting_rate = rc.rate_per_unit
            break

    # If out_date <= inward_date, we just return a single segment of 0 days billing 1.0 month.
    if out_date <= inward_date:
        return [{
            'period_from': inward_date,
            'period_to': out_date,
            'rate_per_unit': starting_rate,
            'days_stored': 0,
            'period': Decimal('1.0'),
            'amount': (Decimal(qty) * starting_rate * Decimal('1.0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        }]

    # 2. Filter rate changes: inward_date < effective_from < out_date
    mid_changes = []
    for rc in rate_changes:
        if inward_date < rc.effective_from < out_date:
            mid_changes.append(rc)

    # Sort mid_changes by effective_from ascending
    mid_changes = sorted(mid_changes, key=lambda x: x.effective_from)

    # 3. Build segments: [inward_date, c1), [c1, c2), ..., [cn, out_date]
    segments = []
    current_start = inward_date
    current_rate = starting_rate

    for rc in mid_changes:
        segments.append({
            'period_from': current_start,
            'period_to': rc.effective_from,
            'rate_per_unit': current_rate,
        })
        current_start = rc.effective_from
        current_rate = rc.rate_per_unit

    segments.append({
        'period_from': current_start,
        'period_to': out_date,
        'rate_per_unit': current_rate,
    })

    # 4. Compute days and period for each segment.
    # Round that segment up to the next half month: ceil(segment_days / 15) / 2.
    for seg in segments:
        days = (seg['period_to'] - seg['period_from']).days
        seg['days_stored'] = days
        ceil_days_div_15 = -(-days // 15)
        seg['period'] = Decimal(ceil_days_div_15) / Decimal('2')

    # 5. Apply the one-month minimum to the whole stay.
    total_period = sum(seg['period'] for seg in segments)
    if total_period < Decimal('1.0'):
        # Because each segment rounds up to at least 0.5 month if days >= 1,
        # total_period < 1.0 is only possible if there is exactly 1 segment.
        segments = [{
            'period_from': inward_date,
            'period_to': out_date,
            'rate_per_unit': starting_rate,
            'days_stored': (out_date - inward_date).days,
            'period': Decimal('1.0'),
        }]

    # 6. Compute amount for each segment and quantize to 2 decimal places.
    for seg in segments:
        seg['amount'] = (Decimal(qty) * seg['rate_per_unit'] * seg['period']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return segments


def compute_segmented_rent(
    *,
    qty: int,
    intake_rate: Decimal,
    rate_changes: list,
    inward_date: date,
    out_date: date
) -> Decimal:
    """
    Compute rent across rate segments. Given a lot's inward date, its intake rate,
    its ordered rate changes, and an out date.

    Known Consequence: because each segment rounds up independently, a stay split
    into N segments can bill up to 0.5 months more than the same unsplit stay per
    extra segment. That is accepted — it matches the legacy behaviour and rate
    changes are roughly annual — but it should be written down rather than discovered
    later.
    """
    segments = compute_segmented_rent_details(
        qty=qty,
        intake_rate=intake_rate,
        rate_changes=rate_changes,
        inward_date=inward_date,
        out_date=out_date,
    )
    return sum(seg['amount'] for seg in segments)

