from datetime import date

def fy_label(d: date) -> str:
    """
    Returns the fiscal year label (1 April to 31 March) for a given date in the format YYYY-YY.
    Example: date(2026, 4, 1) -> "2026-27"
             date(2026, 3, 31) -> "2025-26"
    """
    if d.month >= 4:
        start_year = d.year
    else:
        start_year = d.year - 1
    
    end_year = start_year + 1
    return f"{start_year}-{end_year % 100:02d}"

def fy_bounds(label: str) -> tuple[date, date]:
    """
    Returns the start and end dates (1 April to 31 March) for a given FY label.
    Example: "2026-27" -> (date(2026, 4, 1), date(2027, 3, 31))
    """
    parts = label.split('-')
    if len(parts) != 2:
        raise ValueError(f"Invalid FY label format: {label}")
    
    start_year = int(parts[0])
    # Validate the suffix to ensure it is the next year's last two digits
    expected_suffix = f"{(start_year + 1) % 100:02d}"
    if parts[1] != expected_suffix:
        raise ValueError(f"Invalid FY label suffix: expected {expected_suffix}, got {parts[1]}")
        
    return date(start_year, 4, 1), date(start_year + 1, 3, 31)

def fy_for_date(d: date) -> tuple[str, date, date]:
    """
    Returns the FY label and boundaries for a given date.
    """
    label = fy_label(d)
    start_date, end_date = fy_bounds(label)
    return label, start_date, end_date

def state_code_from_gstin(gstin: str) -> str:
    """
    Extracts the 2-digit state code from a GSTIN.
    """
    if gstin:
        clean_gstin = str(gstin).strip()
        if len(clean_gstin) >= 2 and clean_gstin[:2].isdigit():
            return clean_gstin[:2]
    return ""
