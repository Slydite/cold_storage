from django.db.models import QuerySet
from .models import Chamber, Floor, Block


def get_chambers_list(facility_id: int = None, is_active: bool = None) -> QuerySet[Chamber]:
    """
    Fetch chambers with optional facility_id filtering.
    """
    qs = Chamber.objects.select_related('facility')
    if facility_id is not None:
        qs = qs.filter(facility_id=facility_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def get_chamber_by_id(chamber_id: int) -> Chamber:
    """
    Fetch a chamber by ID.
    """
    return Chamber.objects.select_related('facility').get(pk=chamber_id)


def get_floors_list(
    chamber_id: int = None,
    facility_id: int = None,
    is_active: bool = None
) -> QuerySet[Floor]:
    """
    Fetch floors with optional chamber_id and/or facility_id filtering.
    Floors filtered by facility go through chamber__facility_id.
    """
    qs = Floor.objects.select_related('chamber', 'chamber__facility')
    if chamber_id is not None:
        qs = qs.filter(chamber_id=chamber_id)
    if facility_id is not None:
        qs = qs.filter(chamber__facility_id=facility_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def get_floor_by_id(floor_id: int) -> Floor:
    """
    Fetch a floor by ID.
    """
    return Floor.objects.select_related('chamber', 'chamber__facility').get(pk=floor_id)


def get_blocks_list(
    floor_id: int = None,
    chamber_id: int = None,
    facility_id: int = None,
    is_active: bool = None
) -> QuerySet[Block]:
    """
    Fetch blocks with optional floor_id, chamber_id, and/or facility_id filtering.
    """
    qs = Block.objects.select_related('floor', 'floor__chamber', 'floor__chamber__facility')
    if floor_id is not None:
        qs = qs.filter(floor_id=floor_id)
    if chamber_id is not None:
        qs = qs.filter(floor__chamber_id=chamber_id)
    if facility_id is not None:
        qs = qs.filter(floor__chamber__facility_id=facility_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def get_block_by_id(block_id: int) -> Block:
    """
    Fetch a block by ID.
    """
    return Block.objects.select_related('floor', 'floor__chamber', 'floor__chamber__facility').get(pk=block_id)

