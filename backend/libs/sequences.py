from django.db import transaction
from django.core.exceptions import ValidationError
from apps.facilities.models import Facility
from apps.inventory.models import Sequence

@transaction.atomic
def get_next_sequence_number(
    facility_id: int = None,
    sequence_type: str = '',
    prefix: str = None,
    facility: Facility = None,
) -> str:
    """
    Generate the next sequence number for a given facility and sequence type (e.g. 'GRN', 'DN', 'INV')
    using select_for_update() on the Sequence model inside an atomic transaction.
    Format example: GRN-00001

    Pass an already-loaded `facility` to skip a redundant lookup when the caller
    has one on hand; otherwise pass `facility_id` and it will be fetched here.
    """
    if facility is None:
        try:
            facility = Facility.objects.get(pk=facility_id)
        except Facility.DoesNotExist:
            raise ValidationError(f"Facility with ID {facility_id} does not exist.")

    default_prefix = prefix if prefix is not None else f"{sequence_type}-"

    seq, created = Sequence.objects.select_for_update().get_or_create(
        facility=facility,
        sequence_type=sequence_type,
        defaults={'prefix': default_prefix, 'current_value': 0}
    )

    if prefix is not None and seq.prefix != prefix:
        seq.prefix = prefix

    seq.current_value += 1
    seq.save()

    return f"{seq.prefix}{seq.current_value:05d}"
