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
    """
    return compute_line_rent(
        qty=delivery_line.qty,
        rate_per_unit_per_month=delivery_line.lot.rent_rate_per_unit,
        inward_date=delivery_line.lot.inward_date,
        out_date=delivery_line.delivery_note.dispatch_date,
    )
