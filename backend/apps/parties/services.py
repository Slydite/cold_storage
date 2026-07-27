from django.db import transaction
from django.core.exceptions import ValidationError
from libs.lookups import get_facility_or_raise
from libs.sequences import get_next_sequence_number
from libs.sanitizers import (
    clean_text,
    title_name,
    clean_gstin,
    clean_phone,
    clean_email,
)
from .models import Party

@transaction.atomic
def create_party(
    *,
    facility_id: int,
    name: str,
    type: str,
    phone: str = "",
    email: str = "",
    address: str = "",
    gstin: str = "",
    is_active: bool = True
) -> Party:
    """
    Create a new party for a facility.
    Generates party code automatically using sequence helper.
    """
    facility = get_facility_or_raise(facility_id)

    # Validate party type
    if type not in Party.PartyType.values:
        raise ValidationError(f"Invalid party type: {type}. Allowed values: {Party.PartyType.values}")

    # Sanitise inputs
    name = title_name(name)
    phone = clean_phone(phone)
    email = clean_email(email)
    address = clean_text(address)
    gstin = clean_gstin(gstin)

    # Auto-generate code
    code = get_next_sequence_number(facility=facility, sequence_type='PARTY')

    # Build and clean
    party = Party(
        facility=facility,
        name=name,
        code=code,
        type=type,
        phone=phone,
        email=email,
        address=address,
        gstin=gstin,
        is_active=is_active
    )
    party.full_clean()
    party.save()
    return party

@transaction.atomic
def update_party(*, party_id: int, **fields) -> Party:
    """
    Update an existing party.
    """
    try:
        party = Party.objects.get(pk=party_id)
    except Party.DoesNotExist:
        raise ValidationError(f"Party with ID {party_id} does not exist.")

    # Sanitise provided fields
    if 'name' in fields and fields['name'] is not None:
        fields['name'] = title_name(fields['name'])
    if 'gstin' in fields and fields['gstin'] is not None:
        fields['gstin'] = clean_gstin(fields['gstin'])
    if 'email' in fields and fields['email'] is not None:
        fields['email'] = clean_email(fields['email'])
    if 'phone' in fields and fields['phone'] is not None:
        fields['phone'] = clean_phone(fields['phone'])
    if 'address' in fields and fields['address'] is not None:
        fields['address'] = clean_text(fields['address'])

    # Update allowed fields (code is read-only / auto-generated and cannot be mutated)
    allowed_fields = ['name', 'type', 'phone', 'email', 'address', 'gstin', 'is_active']
    for field, value in fields.items():
        if field in allowed_fields:
            if field == 'type' and value not in Party.PartyType.values:
                raise ValidationError(f"Invalid party type: {value}")
            setattr(party, field, value)
            
    party.full_clean()
    party.save()
    return party

