from django.db import transaction
from django.core.exceptions import ValidationError
from libs.lookups import get_facility_or_raise
from libs.sequences import get_next_sequence_number
from libs.sanitizers import title_name
from .models import Chamber, Floor, Block


@transaction.atomic
def create_chamber(
    *,
    facility_id: int,
    name: str,
    sort_order: int = 0,
    is_active: bool = True
) -> Chamber:
    """
    Create a new chamber for a facility.
    Generates chamber code automatically using sequence helper.
    """
    facility = get_facility_or_raise(facility_id)
    name = title_name(name)
    code = get_next_sequence_number(facility=facility, sequence_type='CHAMBER')

    chamber = Chamber(
        facility=facility,
        name=name,
        code=code,
        sort_order=sort_order,
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
        chamber = Chamber.objects.select_related('facility').get(pk=chamber_id)
    except Chamber.DoesNotExist:
        raise ValidationError(f"Chamber with ID {chamber_id} does not exist.")

    if facility_id is not None and chamber.facility_id != facility_id:
        raise ValidationError(f"Chamber with ID {chamber_id} does not belong to facility {facility_id}.")

    if 'name' in fields and fields['name'] is not None:
        fields['name'] = title_name(fields['name'])

    allowed_fields = ['name', 'sort_order', 'is_active']
    for field, value in fields.items():
        if field in allowed_fields and value is not None:
            setattr(chamber, field, value)

    chamber.full_clean()
    chamber.save()
    return chamber


@transaction.atomic
def create_floor(
    *,
    facility_id: int = None,
    chamber_id: int,
    name: str,
    sort_order: int = 0,
    is_active: bool = True
) -> Floor:
    """
    Create a new floor under a chamber.
    Validates chamber exists and belongs to facility (if facility_id provided).
    Generates floor code automatically using sequence helper.
    """
    try:
        chamber = Chamber.objects.select_related('facility').get(pk=chamber_id)
    except Chamber.DoesNotExist:
        raise ValidationError(f"Chamber with ID {chamber_id} does not exist.")

    if facility_id is not None:
        facility = get_facility_or_raise(facility_id)
        if chamber.facility_id != facility.id:
            raise ValidationError(f"Chamber with ID {chamber_id} does not belong to facility {facility.id}.")

    name = title_name(name)
    code = get_next_sequence_number(facility=chamber.facility, sequence_type='FLOOR')

    floor = Floor(
        chamber=chamber,
        name=name,
        code=code,
        sort_order=sort_order,
        is_active=is_active
    )
    floor.full_clean()
    floor.save()
    return floor


@transaction.atomic
def update_floor(*, floor_id: int, facility_id: int = None, **fields) -> Floor:
    """
    Update an existing floor.
    """
    try:
        floor = Floor.objects.select_related('chamber').get(pk=floor_id)
    except Floor.DoesNotExist:
        raise ValidationError(f"Floor with ID {floor_id} does not exist.")

    if facility_id is not None and floor.chamber.facility_id != facility_id:
        raise ValidationError(f"Floor with ID {floor_id} does not belong to facility {facility_id}.")

    if 'chamber_id' in fields and fields['chamber_id'] is not None:
        new_chamber_id = fields['chamber_id']
        try:
            new_chamber = Chamber.objects.get(pk=new_chamber_id)
        except Chamber.DoesNotExist:
            raise ValidationError(f"Chamber with ID {new_chamber_id} does not exist.")

        target_facility_id = facility_id if facility_id is not None else floor.chamber.facility_id
        if new_chamber.facility_id != target_facility_id:
            raise ValidationError(f"Chamber with ID {new_chamber_id} does not belong to facility {target_facility_id}.")
        floor.chamber = new_chamber

    if 'name' in fields and fields['name'] is not None:
        fields['name'] = title_name(fields['name'])

    allowed_fields = ['name', 'sort_order', 'is_active']
    for field, value in fields.items():
        if field in allowed_fields and value is not None:
            setattr(floor, field, value)

    floor.full_clean()
    floor.save()
    return floor


@transaction.atomic
def create_block(
    *,
    facility_id: int = None,
    chamber_id: int = None,
    floor_id: int,
    name: str,
    sort_order: int = 0,
    capacity_bags: int = None,
    is_active: bool = True
) -> Block:
    """
    Create a new block under a floor.
    Validates floor exists, chamber matches (if chamber_id provided), and facility matches (if facility_id provided).
    Generates block code automatically using sequence helper.
    """
    try:
        floor = Floor.objects.select_related('chamber__facility').get(pk=floor_id)
    except Floor.DoesNotExist:
        raise ValidationError(f"Floor with ID {floor_id} does not exist.")

    if chamber_id is not None and floor.chamber_id != chamber_id:
        raise ValidationError(f"Floor with ID {floor_id} does not belong to chamber {chamber_id}.")

    if facility_id is not None:
        facility = get_facility_or_raise(facility_id)
        if floor.chamber.facility_id != facility.id:
            raise ValidationError(f"Floor with ID {floor_id} does not belong to facility {facility.id}.")

    name = title_name(name)
    code = get_next_sequence_number(facility=floor.chamber.facility, sequence_type='BLOCK')

    block = Block(
        floor=floor,
        name=name,
        code=code,
        sort_order=sort_order,
        capacity_bags=capacity_bags,
        is_active=is_active
    )
    block.full_clean()
    block.save()
    return block


@transaction.atomic
def update_block(*, block_id: int, facility_id: int = None, **fields) -> Block:
    """
    Update an existing block.
    """
    try:
        block = Block.objects.select_related('floor__chamber').get(pk=block_id)
    except Block.DoesNotExist:
        raise ValidationError(f"Block with ID {block_id} does not exist.")

    if facility_id is not None and block.floor.chamber.facility_id != facility_id:
        raise ValidationError(f"Block with ID {block_id} does not belong to facility {facility_id}.")

    if 'floor_id' in fields and fields['floor_id'] is not None:
        new_floor_id = fields['floor_id']
        try:
            new_floor = Floor.objects.select_related('chamber').get(pk=new_floor_id)
        except Floor.DoesNotExist:
            raise ValidationError(f"Floor with ID {new_floor_id} does not exist.")

        target_facility_id = facility_id if facility_id is not None else block.floor.chamber.facility_id
        if new_floor.chamber.facility_id != target_facility_id:
            raise ValidationError(f"Floor with ID {new_floor_id} does not belong to facility {target_facility_id}.")
        block.floor = new_floor

    if 'name' in fields and fields['name'] is not None:
        fields['name'] = title_name(fields['name'])

    allowed_fields = ['name', 'sort_order', 'capacity_bags', 'is_active']
    for field, value in fields.items():
        if field in allowed_fields and value is not None:
            setattr(block, field, value)

    block.full_clean()
    block.save()
    return block


