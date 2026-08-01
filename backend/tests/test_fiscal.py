from datetime import date
import pytest
from libs.fiscal import fy_label, fy_bounds, fy_for_date, state_code_from_gstin

def test_fy_label():
    # Boundary cases: 31 Mar / 1 Apr
    assert fy_label(date(2026, 3, 31)) == "2025-26"
    assert fy_label(date(2026, 4, 1)) == "2026-27"
    assert fy_label(date(2025, 3, 31)) == "2024-25"
    assert fy_label(date(2025, 4, 1)) == "2025-26"
    
    # Leap year case (2024 is a leap year)
    assert fy_label(date(2024, 2, 29)) == "2023-24"
    assert fy_label(date(2024, 3, 31)) == "2023-24"
    assert fy_label(date(2024, 4, 1)) == "2024-25"
    
    # Normal dates
    assert fy_label(date(2026, 8, 15)) == "2026-27"
    assert fy_label(date(2026, 12, 31)) == "2026-27"
    assert fy_label(date(2027, 1, 1)) == "2026-27"

def test_fy_bounds():
    assert fy_bounds("2026-27") == (date(2026, 4, 1), date(2027, 3, 31))
    assert fy_bounds("2025-26") == (date(2025, 4, 1), date(2026, 3, 31))
    assert fy_bounds("2023-24") == (date(2023, 4, 1), date(2024, 3, 31))
    
    # Invalid formats
    with pytest.raises(ValueError):
        fy_bounds("2026")
    with pytest.raises(ValueError):
        fy_bounds("2026-28")
    with pytest.raises(ValueError):
        fy_bounds("2026-abc")

def test_fy_for_date():
    label, start, end = fy_for_date(date(2026, 8, 1))
    assert label == "2026-27"
    assert start == date(2026, 4, 1)
    assert end == date(2027, 3, 31)
    
    label, start, end = fy_for_date(date(2026, 3, 31))
    assert label == "2025-26"
    assert start == date(2025, 4, 1)
    assert end == date(2026, 3, 31)

def test_state_code_from_gstin():
    assert state_code_from_gstin("09AAAAA1111A1Z1") == "09"
    assert state_code_from_gstin("27AAAAA1111A1Z1") == "27"
    assert state_code_from_gstin("  27AAAAA1111A1Z1 ") == "27"
    assert state_code_from_gstin("9A") == ""
    assert state_code_from_gstin("A9") == ""
    assert state_code_from_gstin("") == ""
    assert state_code_from_gstin(None) == ""
