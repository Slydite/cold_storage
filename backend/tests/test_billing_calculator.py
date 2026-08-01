from datetime import date
from decimal import Decimal
import pytest

from apps.billing.services import billable_multiplier, days_stored, compute_line_rent


def test_billable_multiplier_required_behaviour():
    """
    Assert the required behaviour table exactly:
    | elapsed days | period |
    |---|---|
    | 0 | 1.0 |
    | 1 | 1.0 |
    | 15 | 1.0 |
    | 29 | 1.0 |
    | 30 | 1.0 |
    | 31 | 1.5 |
    | 45 | 1.5 |
    | 46 | 2.0 |
    | 60 | 2.0 |
    | 71 | 2.5 |
    | 90 | 3.0 |
    | 120 | 4.0 |
    | 180 | 6.0 |
    | 240 | 8.0 |
    | 300 | 10.0 |
    """
    expected_periods = {
        0: Decimal('1.0'),
        1: Decimal('1.0'),
        15: Decimal('1.0'),
        29: Decimal('1.0'),
        30: Decimal('1.0'),
        31: Decimal('1.5'),
        45: Decimal('1.5'),
        46: Decimal('2.0'),
        60: Decimal('2.0'),
        71: Decimal('2.5'),
        90: Decimal('3.0'),
        120: Decimal('4.0'),
        180: Decimal('6.0'),
        240: Decimal('8.0'),
        300: Decimal('10.0'),
    }
    for days, period in expected_periods.items():
        assert billable_multiplier(days) == period, f"Failed for {days} days"


def test_billable_multiplier_boundaries():
    """
    Test both sides of at least three boundaries:
    - 30 days -> 1.0 vs 31 days -> 1.5
    - 45 days -> 1.5 vs 46 days -> 2.0
    - 60 days -> 2.0 vs 61 days -> 2.5
    - 75 days -> 2.5 vs 76 days -> 3.0
    """
    # Boundary 1
    assert billable_multiplier(30) == Decimal('1.0')
    assert billable_multiplier(31) == Decimal('1.5')

    # Boundary 2
    assert billable_multiplier(45) == Decimal('1.5')
    assert billable_multiplier(46) == Decimal('2.0')

    # Boundary 3
    assert billable_multiplier(60) == Decimal('2.0')
    assert billable_multiplier(61) == Decimal('2.5')

    # Boundary 4
    assert billable_multiplier(75) == Decimal('2.5')
    assert billable_multiplier(76) == Decimal('3.0')


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
    # With non-inclusive elapsed day counting: 34 elapsed days is Jan 1 to Feb 4
    out = date(2026, 2, 4)
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
        out_date=date(2026, 1, 31)  # 30 elapsed days
    )
    assert rent == Decimal('1.00')


def test_legacy_regression():
    """
    Add a regression test that pins the formula to the legacy system cases.
    Legacy cases (elapsed days -> period actually billed):
    (76, 2.5)   (63, 2.0)   (71, 2.5)   (30, 1.0)   (240, 8.0)

    Under the owner's new rules:
    - Grace days were explicitly rejected (no grace days subtracted).
    - Calendar-month divisor (30.4375) was rejected in favor of a 30-day month.
    Therefore, the formula is: period = max(1.0, ceil(days / 15) / 2).
    This matches legacy values exactly for 71 -> 2.5, 30 -> 1.0, and 240 -> 8.0.
    For 76 and 63, the new formula yields 3.0 and 2.5 (instead of legacy 2.5 and 2.0).
    We assert these new expected outcomes to pin the new formula.
    """
    assert billable_multiplier(76) == Decimal('3.0')
    assert billable_multiplier(63) == Decimal('2.5')
    assert billable_multiplier(71) == Decimal('2.5')
    assert billable_multiplier(30) == Decimal('1.0')
    assert billable_multiplier(240) == Decimal('8.0')
