from django.db import transaction
from .models import Facility

@transaction.atomic
def create_facility(
    *,
    name: str,
    code: str,
    address: str = "",
    gstin: str = "",
    phone: str = "",
    factory_phone: str = "",
    bank_account_no: str = "",
    bank_ifsc: str = "",
    terms_and_conditions: str = ""
) -> Facility:
    """
    Create a new facility.
    """
    facility = Facility(
        name=name,
        code=code,
        address=address,
        gstin=gstin,
        phone=phone,
        factory_phone=factory_phone,
        bank_account_no=bank_account_no,
        bank_ifsc=bank_ifsc,
        terms_and_conditions=terms_and_conditions
    )
    facility.full_clean()
    facility.save()
    return facility

@transaction.atomic
def update_facility(*, facility_id: int, **fields) -> Facility:
    """
    Update an existing facility.
    """
    facility = Facility.objects.get(pk=facility_id)
    
    # Update allowed fields
    allowed_fields = [
        'name', 'code', 'address', 'gstin', 'phone',
        'factory_phone', 'bank_account_no', 'bank_ifsc', 'terms_and_conditions'
    ]
    for field, value in fields.items():
        if field in allowed_fields:
            setattr(facility, field, value)
            
    facility.full_clean()
    facility.save()
    return facility

