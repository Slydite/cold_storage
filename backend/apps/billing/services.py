import math
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


def billable_multiplier(days_stored: int) -> Decimal:
    """
    Calculate the rent multiplier based on days in storage (RULE 1).

    Rent Formula (Owner's Rule):
    - Minimum 30 days floor: days_stored <= 30 (including 0 or negative for same-day/erroneous dates)
      receives a multiplier of 1.0. Documented assumption: same-day in-and-out still pays the 30-day
      minimum floor per the business rule "minimum 30 days".
    - After the first 30 days, billing is charged by every 15 days minimum slab (30, 45, 60, 75, ...):
      multiplier = Decimal('1.0') + Decimal('0.5') * Decimal(math.ceil((days_stored - 30) / 15))
    
    Examples:
    - 1 to 30 days -> 1.0
    - 31 to 45 days -> 1.5
    - 46 to 60 days -> 2.0
    - 61 to 75 days -> 2.5
    """
    if days_stored <= 30:
        return Decimal('1.0')
    
    slabs = math.ceil((days_stored - 30) / 15)
    return Decimal('1.0') + Decimal('0.5') * Decimal(slabs)


def days_stored(inward_date: date, out_date: date) -> int:
    """
    Calculate the number of days stock was stored between inward_date and out_date.

    Day Counting Decision:
    Uses inclusive day counting: `(out_date - inward_date).days + 1`.

    Rationale:
    In cold storage operations, both the day of receipt (GRN) and the day of dispatch (DN) involve
    space allocation and handling overhead on those calendar days. For instance, goods received on
    Jan 1 and withdrawn on Jan 1 were present in the storage facility for 1 calendar day.
    Because the 30-day minimum floor guards any duration up to 30 days (multiplier 1.0), this +1
    affects slab transitions predictably (e.g., June 1 to June 30 is 30 days inclusive; June 1 to
    July 1 is 31 days inclusive, triggering the first 15-day slab).
    """
    if out_date < inward_date:
        return 0
    return (out_date - inward_date).days + 1


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
