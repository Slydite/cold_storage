"""
The one implementation of the lot-number format.

Lot numbers are what customers read off the bags, so they follow the shape the
business has used for years, dated and zero-padded:

    {receipt date YYYYMMDD}-{serial 5 digits}-{bags 5 digits}
    e.g. 20260725-02606-00594

The legacy system's serial is a running counter (1 in June 2010, 2606 by July
2026) that is not strictly monotonic - low serials get reused across years -
which is why the date is part of the identifier rather than decoration. With
the date included, this format is more unique across the legacy extract than
the raw FAS string it replaces.

Both the ETL and `create_grn` build numbers in this format. Keeping the rule
here means they cannot drift apart.
"""
import re
from datetime import date

SERIAL_DIGITS = 5
BAGS_DIGITS = 5
MAX_SERIAL = 10 ** SERIAL_DIGITS - 1  # 99999
MAX_BAGS = 10 ** BAGS_DIGITS - 1      # 99999

# Trailing suffix is reserved for disambiguating imported duplicates.
LOT_NUMBER_RE = re.compile(r'^\d{8}-\d{5}-\d{5}(?:-[A-Z]+)?$')


def clamp_serial(serial: int) -> tuple[int, str]:
    """
    Fit a serial into its field, reporting rather than silently mangling.

    Truncating 222265 to 22226 would yield a plausible-looking lot number that
    is simply wrong and would never be noticed, so an oversized serial is
    pinned to the maximum and the original is named in the returned warning.
    Two such values exist in seventeen years of legacy data, both typos.
    """
    if serial < 0:
        return 0, f"Negative serial {serial} treated as 0"
    if serial > MAX_SERIAL:
        return MAX_SERIAL, f"Oversized serial clamped to {MAX_SERIAL} (original: {serial})"
    return serial, ""


def clamp_bags(bags: int) -> tuple[int, str]:
    """As clamp_serial, for the bag-count field."""
    if bags < 0:
        return 0, f"Negative quantity {bags} treated as 0"
    if bags > MAX_BAGS:
        return MAX_BAGS, f"Oversized quantity clamped to {MAX_BAGS} (original: {bags})"
    return bags, ""


def build_lot_number(*, receipt_date: date, serial: int, bags: int) -> tuple[str, str]:
    """
    Return (lot_number, warning). The warning is empty when nothing was clamped.

    The result always matches LOT_NUMBER_RE - callers may rely on that, which
    is the point of clamping rather than letting an oversized value widen the
    field and produce a number the format's own validation would reject.
    """
    serial, serial_warning = clamp_serial(serial)
    bags, bags_warning = clamp_bags(bags)
    warning = '; '.join(w for w in (serial_warning, bags_warning) if w)
    lot_number = f"{receipt_date.strftime('%Y%m%d')}-{serial:0{SERIAL_DIGITS}d}-{bags:0{BAGS_DIGITS}d}"
    return lot_number, warning


def is_valid_lot_number(value: str) -> bool:
    return bool(LOT_NUMBER_RE.match(value or ''))
