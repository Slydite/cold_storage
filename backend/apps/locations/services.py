from django.db import transaction
from django.core.exceptions import ValidationError
from libs.lookups import get_facility_or_raise
from .models import Floor, Chamber


@transaction.atomic
def create_floor(
    *,
    facility_id: int,
    name: str,
    sort_order: int = 0,
    is_active: bool = True
) -> Floor:
    """
    Create a new floor for a facility.
    """
    facility = get_facility_or_raise(facility_id)

    floor = Floor(
        facility=facility,
        name=name,
        sort_order=sort_order,
        is_active=is_active
    )
    floor.full_clean()
    floor.save()
    return floor


@transaction.atomic
def update_floor(*, floor_id: int, **fields) -> Floor:
    """
    Update an existing floor.
    """
    try:
        floor = Floor.objects.get(pk=floor_id)
    except Floor.DoesNotExist:
        raise ValidationError(f"Floor with ID {floor_id} does not exist.")

    allowed_fields = ['name', 'sort_order', 'is_active']
    for field, value in fields.items():
        if field in allowed_fields and value is not None:
            setattr(floor, field, value)

    floor.full_clean()
    floor.save()
    return floor


@transaction.atomic
def create_chamber(
    *,
    facility_id: int,
    floor_id: int,
    name: str,
    sort_order: int = 0,
    capacity_bags: int = None,
    is_active: bool = True
) -> Chamber:
    """
    Create a new chamber under a floor for a facility.
    Validates facility exists and floor exists & belongs to facility.
    """
    facility = get_facility_or_raise(facility_id)

    try:
        floor = Floor.objects.get(pk=floor_id)
    except Floor.DoesNotExist:
        raise ValidationError(f"Floor with ID {floor_id} does not exist.")

    if floor.facility_id != facility.id:
        raise ValidationError(f"Floor with ID {floor_id} does not belong to facility {facility.id}.")

    chamber = Chamber(
        floor=floor,
        name=name,
        sort_order=sort_order,
        capacity_bags=capacity_bags,
        is_active=is_active
    )
    chamber.full_clean()
    chamber.save()
    return chamber


@transaction.atomic
def update_chamber(*, chamber_id: int, facility_id: int = None, **fields) -> Chamber:
    """
    Update an existing chamber.
    """
    try:
        chamber = Chamber.objects.select_related('floor').get(pk=chamber_id)
    except Chamber.DoesNotExist:
        raise ValidationError(f"Chamber with ID {chamber_id} does not exist.")

    if facility_id is not None and chamber.floor.facility_id != facility_id:
        raise ValidationError(f"Chamber with ID {chamber_id} does not belong to facility {facility_id}.")

    if 'floor_id' in fields and fields['floor_id'] is not None:
        new_floor_id = fields['floor_id']
        try:
            new_floor = Floor.objects.get(pk=new_floor_id)
        except Floor.DoesNotExist:
            raise ValidationError(f"Floor with ID {new_floor_id} does not exist.")
        
        target_facility_id = facility_id if facility_id is not None else chamber.floor.facility_id
        if new_floor.facility_id != target_facility_id:
            raise ValidationError(f"Floor with ID {new_floor_id} does not belong to facility {target_facility_id}.")
        chamber.floor = new_floor

    allowed_fields = ['name', 'sort_order', 'capacity_bags', 'is_active']
    for field, value in fields.items():
        if field in allowed_fields and value is not None:
            setattr(chamber, field, value)

    chamber.full_clean()
    chamber.save()
    return chamber
