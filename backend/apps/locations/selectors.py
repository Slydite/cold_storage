from django.db.models import QuerySet
from .models import Floor, Chamber


def get_floors_list(facility_id: int, is_active: bool = None) -> QuerySet[Floor]:
    """
    Fetch all floors for a facility.
    """
    qs = Floor.objects.filter(facility_id=facility_id).select_related('facility')
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def get_floor_by_id(floor_id: int) -> Floor:
    """
    Fetch a floor by ID.
    """
    return Floor.objects.select_related('facility').get(pk=floor_id)


def get_chambers_list(facility_id: int = None, floor_id: int = None, is_active: bool = None) -> QuerySet[Chamber]:
    """
    Fetch chambers with optional facility_id and/or floor_id filtering.
    Chambers filtered by facility go through floor__facility_id.
    """
    qs = Chamber.objects.select_related('floor', 'floor__facility')
    if facility_id is not None:
        qs = qs.filter(floor__facility_id=facility_id)
    if floor_id is not None:
        qs = qs.filter(floor_id=floor_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def get_chamber_by_id(chamber_id: int) -> Chamber:
    """
    Fetch a chamber by ID.
    """
    return Chamber.objects.select_related('floor', 'floor__facility').get(pk=chamber_id)
