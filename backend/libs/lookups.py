from django.core.exceptions import ValidationError
from apps.facilities.models import Facility
from apps.parties.models import Party


def get_facility_or_raise(facility_id: int) -> Facility:
    """
    Fetch a Facility by ID or raise ValidationError.
    """
    try:
        return Facility.objects.get(pk=facility_id)
    except Facility.DoesNotExist:
        raise ValidationError(f"Facility with ID {facility_id} does not exist.")


def get_party_or_raise(party_id: int, facility: Facility) -> Party:
    """
    Fetch a Party by ID scoped to a facility or raise ValidationError.
    """
    try:
        return Party.objects.get(pk=party_id, facility=facility)
    except Party.DoesNotExist:
        raise ValidationError(f"Party with ID {party_id} does not exist in facility {facility.id}.")
