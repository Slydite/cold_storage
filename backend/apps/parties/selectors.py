from django.db.models import QuerySet
from .models import Party

def get_party_by_id(party_id: int) -> Party:
    """
    Fetch a single party by its primary key.
    """
    return Party.objects.get(pk=party_id)

def get_parties_list(
    *,
    facility_id: int,
    type: str = None,
    is_active: bool = None
) -> QuerySet[Party]:
    """
    Get all parties, filtered by facility, and optional type/is_active filters.
    """
    queryset = Party.objects.filter(facility_id=facility_id)

    if type is not None:
        queryset = queryset.filter(type=type)

    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)

    return queryset.order_by('name')
