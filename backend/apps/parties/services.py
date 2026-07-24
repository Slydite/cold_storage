from django.db import transaction
from django.core.exceptions import ValidationError
from libs.lookups import get_facility_or_raise
from .models import Party

@transaction.atomic
def create_party(
    *,
    facility_id: int,
    name: str,
    code: str,
    type: str,
    phone: str = "",
    email: str = "",
    address: str = "",
    is_active: bool = True
) -> Party:
    """
    Create a new party for a facility.
    """
    facility = get_facility_or_raise(facility_id)

    # Validate party type
    if type not in Party.PartyType.values:
        raise ValidationError(f"Invalid party type: {type}. Allowed values: {Party.PartyType.values}")

    # Build and clean
    party = Party(
        facility=facility,
        name=name,
        code=code,
        type=type,
        phone=phone,
        email=email,
        address=address,
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

    # Update allowed fields
    allowed_fields = ['name', 'code', 'type', 'phone', 'email', 'address', 'is_active']
    for field, value in fields.items():
        if field in allowed_fields:
            if field == 'type' and value not in Party.PartyType.values:
                raise ValidationError(f"Invalid party type: {value}")
            setattr(party, field, value)
            
    party.full_clean()
    party.save()
    return party
