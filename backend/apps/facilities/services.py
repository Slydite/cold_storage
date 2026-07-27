from django.db import transaction
from libs.sequences import get_next_sequence_number
from libs.sanitizers import (
    clean_text,
    title_name,
    clean_gstin,
    clean_phone,
    upper_code,
)
from .models import Facility

@transaction.atomic
def create_facility(
    *,
    name: str,
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
    Generates facility code automatically using global sequence lock.
    """
    name = title_name(name)
    gstin = clean_gstin(gstin)
    phone = clean_phone(phone)
    factory_phone = clean_phone(factory_phone)
    bank_ifsc = upper_code(bank_ifsc)
    address = clean_text(address)
    terms_and_conditions = clean_text(terms_and_conditions)

    code = get_next_sequence_number(facility=None, sequence_type='FACILITY')

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
    
    if 'name' in fields and fields['name'] is not None:
        fields['name'] = title_name(fields['name'])
    if 'gstin' in fields and fields['gstin'] is not None:
        fields['gstin'] = clean_gstin(fields['gstin'])
    if 'phone' in fields and fields['phone'] is not None:
        fields['phone'] = clean_phone(fields['phone'])
    if 'factory_phone' in fields and fields['factory_phone'] is not None:
        fields['factory_phone'] = clean_phone(fields['factory_phone'])
    if 'bank_ifsc' in fields and fields['bank_ifsc'] is not None:
        fields['bank_ifsc'] = upper_code(fields['bank_ifsc'])
    if 'address' in fields and fields['address'] is not None:
        fields['address'] = clean_text(fields['address'])
    if 'terms_and_conditions' in fields and fields['terms_and_conditions'] is not None:
        fields['terms_and_conditions'] = clean_text(fields['terms_and_conditions'])

    # Update allowed fields (code is read-only / auto-generated and cannot be mutated)
    allowed_fields = [
        'name', 'address', 'gstin', 'phone',
        'factory_phone', 'bank_account_no', 'bank_ifsc', 'terms_and_conditions'
    ]
    for field, value in fields.items():
        if field in allowed_fields:
            setattr(facility, field, value)
            
    facility.full_clean()
    facility.save()
    return facility


