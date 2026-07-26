from datetime import date
from decimal import Decimal
import pytest

from apps.billing.services import billable_multiplier, days_stored, compute_line_rent


def test_billable_multiplier_exhaustive_slabs():
    """
    Exhaustive boundary testing for billable_multiplier per Rule 1:
    - 1 day -> 1.0
    - 30 days -> 1.0
    - 31 days -> 1.5
    - 45 days -> 1.5
    - 46 days -> 2.0
    - 60 days -> 2.0
    - 61 days -> 2.5
    - 75 days -> 2.5
    """
    assert billable_multiplier(1) == Decimal('1.0')
    assert billable_multiplier(30) == Decimal('1.0')
    assert billable_multiplier(31) == Decimal('1.5')
    assert billable_multiplier(45) == Decimal('1.5')
    assert billable_multiplier(46) == Decimal('2.0')
    assert billable_multiplier(60) == Decimal('2.0')
    assert billable_multiplier(61) == Decimal('2.5')
    assert billable_multiplier(75) == Decimal('2.5')


def test_billable_multiplier_zero_and_negative_days():
    """
    Asserts zero and negative days (same-day or invalid dates) default to 1.0 multiplier
    because the minimum 30-day floor applies to any withdrawal.
    """
    assert billable_multiplier(0) == Decimal('1.0')
    assert billable_multiplier(-5) == Decimal('1.0')


def test_owner_worked_example_100_bags_rate_12_34_days():
    """
    CANONICAL BUSINESS EXAMPLE approved by the owner:
    100 bags at rate 12 stored 34 days = 1800.
    days = 34 -> 30 days minimum (1.0) + one 15-day slab (+0.5) = multiplier 1.5.
    100 * 12 * 1.5 = 1800.00
    """
    inward = date(2026, 1, 1)
    # With inclusive day counting: 34 days = Jan 1 to Feb 3 (34 - 1 + 1 = 34 days)
    out = date(2026, 2, 3)
    calculated_days = days_stored(inward, out)
    assert calculated_days == 34
    
    multiplier = billable_multiplier(calculated_days)
    assert multiplier == Decimal('1.5')

    rent = compute_line_rent(
        qty=100,
        rate_per_unit_per_month=Decimal('12.00'),
        inward_date=inward,
        out_date=out
    )
    assert rent == Decimal('1800.00')


def test_compute_line_rent_quantization():
    """
    Asserts compute_line_rent rounds HALF_UP to 2 decimal places.
    e.g. qty 3, rate Decimal('0.333'), 30 days (multiplier 1.0):
    3 * 0.333 * 1.0 = 0.999 -> rounds to 1.00.
    """
    rent = compute_line_rent(
        qty=3,
        rate_per_unit_per_month=Decimal('0.333'),
        inward_date=date(2026, 1, 1),
        out_date=date(2026, 1, 30)
    )
    assert rent == Decimal('1.00')
