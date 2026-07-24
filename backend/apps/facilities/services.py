from django.db import transaction
from .models import Facility

@transaction.atomic
def create_facility(*, name: str, code: str, address: str = "") -> Facility:
    """
    Create a new facility.
    """
    facility = Facility(name=name, code=code, address=address)
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
    allowed_fields = ['name', 'code', 'address']
    for field, value in fields.items():
        if field in allowed_fields:
            setattr(facility, field, value)
            
    facility.full_clean()
    facility.save()
    return facility
