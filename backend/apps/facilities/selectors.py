from django.db.models import QuerySet
from .models import Facility

def get_facility_list() -> QuerySet[Facility]:
    """
    Get all facilities.
    """
    return Facility.objects.all().order_by('-created_at')

def get_facility_by_id(facility_id: int) -> Facility:
    """
    Get facility by ID.
    """
    return Facility.objects.get(pk=facility_id)
